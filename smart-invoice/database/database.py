import sqlite3
import os
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger("smart-invoice-db")
DB_PATH = os.path.join(os.path.dirname(__file__), "invoice.db")

def is_werkzeug_hash(val):
    if not isinstance(val, str):
        return False
    val = val.strip()
    return val.startswith(("scrypt:", "pbkdf2:", "argon2:", "sha256:", "gost:")) or (":" in val and len(val) > 20)

def sync_to_firestore(collection_name, doc_id, data_dict):
    """Graceful sync to GCP Firestore Native when running on GCP."""
    try:
        from google.cloud import firestore
        project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project_id) if project_id else firestore.Client()
        db.collection(collection_name).document(str(doc_id)).set(data_dict, merge=True)
        logger.info(f"Successfully synced document {doc_id} to Firestore collection {collection_name}")
    except Exception as e:
        logger.warning(f"Firestore sync deferred/failed for {collection_name}/{doc_id}: {e}")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Registered Clients Roster Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            client_whatsapp TEXT,
            payment_terms_days INTEGER DEFAULT 14,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Registered Freelancer Work Items / Services Catalog Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            hourly_rate REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Invoices table (no legacy UNIQUE constraint on invoice_number alone)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            invoice_number TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            invoice_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            tax_rate REAL DEFAULT 0.0,
            subtotal REAL DEFAULT 0.0,
            grand_total REAL DEFAULT 0.0,
            notes TEXT,
            status TEXT DEFAULT 'PENDING',
            payment_date TEXT,
            pdf_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Invoice Line Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            hours REAL NOT NULL,
            hourly_rate REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
        )
    ''')
    
    # Run schema migration for existing databases
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN pdf_url TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN client_whatsapp TEXT")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()
    
    # Hydrate SQLite database from Firestore on startup
    hydrate_sqlite_from_firestore()

def hydrate_sqlite_from_firestore():
    """
    Hydrates the SQLite database with records from GCP Firestore on startup.
    Ensures state is fully persistent across ephemeral Cloud Run container restarts.
    """
    try:
        from google.cloud import firestore
        project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project_id) if project_id else firestore.Client()
        
        logger.info("Fetching hydration data from GCP Firestore...")
        # 1. Fetch from Firestore first (network calls, no SQLite connection open)
        users = [doc.to_dict() for doc in db.collection("users").stream()]
        clients = [doc.to_dict() for doc in db.collection("clients").stream()]
        services = [doc.to_dict() for doc in db.collection("services").stream()]
        invoices = [doc.to_dict() for doc in db.collection("invoices").stream()]
        
        # 2. Write to SQLite in a single rapid transaction
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Writing Firestore records to SQLite...")
        
        # Hydrate Users
        for u in users:
            pwd_val = u.get("password_hash") or u.get("password") or ""
            uid = u.get("id")
            if uid is not None:
                cursor.execute('''
                    INSERT OR REPLACE INTO users (id, name, email, password_hash)
                    VALUES (?, ?, ?, ?)
                ''', (uid, u.get("name", "User"), (u.get("email") or "").lower().strip(), pwd_val))
            
        # Hydrate Clients
        for c in clients:
            cursor.execute('''
                INSERT OR REPLACE INTO clients (id, user_id, client_name, client_email, client_whatsapp, payment_terms_days, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (c.get("id"), c.get("user_id"), c.get("client_name"), c.get("client_email"), c.get("client_whatsapp"), c.get("payment_terms_days"), c.get("notes")))
            
        # Hydrate Services
        for s in services:
            cursor.execute('''
                INSERT OR REPLACE INTO services (id, user_id, title, hourly_rate, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (s.get("id"), s.get("user_id"), s.get("title"), s.get("hourly_rate"), s.get("description")))
            
        # Hydrate Invoices
        for inv in invoices:
            cursor.execute('''
                INSERT OR REPLACE INTO invoices (id, user_id, invoice_number, client_name, client_email, invoice_date, due_date, tax_rate, subtotal, grand_total, notes, status, payment_date, pdf_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inv.get("id"), inv.get("user_id"), inv.get("invoice_number"), inv.get("client_name"),
                inv.get("client_email"), inv.get("invoice_date"), inv.get("due_date"), inv.get("tax_rate"),
                inv.get("subtotal"), inv.get("grand_total"), inv.get("notes"), inv.get("status"),
                inv.get("payment_date"), inv.get("pdf_url")
            ))
            
            # Clear existing items for this invoice to avoid duplication
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (inv.get("id"),))
            
            # Insert items from Firestore array
            items = inv.get("items", [])
            for item in items:
                cursor.execute('''
                    INSERT INTO invoice_items (invoice_id, description, hours, hourly_rate, amount)
                    VALUES (?, ?, ?, ?, ?)
                ''', (inv.get("id"), item.get("description"), float(item.get("hours", 0)), float(item.get("hourly_rate", 0)), float(item.get("amount", 0))))
                
        conn.commit()
        conn.close()
        logger.info("SQLite database hydration from Firestore complete!")
    except Exception as e:
        logger.warning(f"GCP Firestore hydration skipped or deferred: {e}")

# -------------------------------------------------------------
# USER AUTHENTICATION HELPERS
# -------------------------------------------------------------
def create_user(name, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    pwd_hash = generate_password_hash(password)
    clean_email = email.lower().strip()
    try:
        cursor.execute('''
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        ''', (name, clean_email, pwd_hash))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        user_data = {
            "id": user_id,
            "name": name,
            "email": clean_email,
            "password_hash": pwd_hash,
            "created_at": datetime.now().isoformat()
        }
        sync_to_firestore("users", user_id, user_data)
        
        return user_data
    except sqlite3.IntegrityError:
        conn.close()
        return None

def find_user_in_firestore_by_email(email):
    try:
        from google.cloud import firestore
        project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project_id) if project_id else firestore.Client()
        docs = db.collection("users").where("email", "==", email.lower().strip()).stream()
        for doc in docs:
            d = doc.to_dict()
            if d:
                if not d.get("password_hash") and d.get("password"):
                    d["password_hash"] = d["password"]
                if "id" not in d or d.get("id") is None:
                    try:
                        d["id"] = int(doc.id)
                    except ValueError:
                        d["id"] = doc.id
                return d
    except Exception as e:
        logger.warning(f"Firestore direct user lookup error: {e}")
    return None

def verify_user(email, password):
    clean_email = email.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
    user_row = cursor.fetchone()
    conn.close()
    
    user_dict = dict(user_row) if user_row else None
    
    # Direct fallback to Firestore if user was not found in SQLite or password_hash was empty/dummy
    if not user_dict or not user_dict.get("password_hash") or user_dict.get("password_hash") == "dummy":
        f_user = find_user_in_firestore_by_email(clean_email)
        if f_user:
            user_dict = f_user
            pwd_val = f_user.get("password_hash") or f_user.get("password") or ""
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (id, name, email, password_hash)
                    VALUES (?, ?, ?, ?)
                ''', (f_user.get("id"), f_user.get("name", "User"), clean_email, pwd_val))
                conn.commit()
                conn.close()
            except Exception as ex:
                logger.warning(f"Failed to persist Firestore user to SQLite: {ex}")

    if not user_dict:
        return None

    stored_hash = (user_dict.get("password_hash") or user_dict.get("password") or "").strip()
    if not stored_hash:
        return None

    # 1. Standard Werkzeug check_password_hash check
    if is_werkzeug_hash(stored_hash):
        try:
            if check_password_hash(stored_hash, password):
                return {
                    "id": user_dict["id"],
                    "name": user_dict.get("name", "User"),
                    "email": user_dict.get("email", clean_email)
                }
        except Exception as e:
            logger.warning(f"Password hash check exception: {e}")

    # 2. Plain text password fallback (e.g. if created/edited directly in Firestore console as plain text)
    # ONLY apply if stored_hash is NOT a Werkzeug hash!
    if stored_hash == password and not is_werkzeug_hash(stored_hash):
        new_hash = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_dict["id"]))
            conn.commit()
            conn.close()
        except Exception:
            pass
        sync_to_firestore("users", user_dict["id"], {"password_hash": new_hash})
        return {
            "id": user_dict["id"],
            "name": user_dict.get("name", "User"),
            "email": user_dict.get("email", clean_email)
        }

    # 3. Direct Firestore repair for plain text "password" or corrupted hash
    f_user = find_user_in_firestore_by_email(clean_email)
    if f_user:
        f_plain = (f_user.get("password") or "").strip()
        f_hash = (f_user.get("password_hash") or "").strip()
        
        # If Firestore has plain password matching user input
        if f_plain and f_plain == password:
            new_hash = generate_password_hash(password)
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_dict["id"]))
                conn.commit()
                conn.close()
            except Exception:
                pass
            sync_to_firestore("users", user_dict["id"], {"password_hash": new_hash})
            return {
                "id": user_dict["id"],
                "name": user_dict.get("name", "User"),
                "email": user_dict.get("email", clean_email)
            }
            
        # If Firestore has a valid Werkzeug hash and check_password_hash works on it
        if f_hash and is_werkzeug_hash(f_hash):
            try:
                if check_password_hash(f_hash, password):
                    # Save working hash to SQLite
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (f_hash, user_dict["id"]))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                    return {
                        "id": user_dict["id"],
                        "name": user_dict.get("name", "User"),
                        "email": user_dict.get("email", clean_email)
                    }
            except Exception:
                pass

    return None



def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# -------------------------------------------------------------
# REGISTERED CLIENTS HELPERS
# -------------------------------------------------------------
def create_client(user_id, client_name, client_email="", client_whatsapp="", payment_terms_days=14, notes=""):
    # If 4th arg is numeric (legacy call format where 4th arg was payment_terms_days), re-map parameters:
    if isinstance(client_whatsapp, (int, float)):
        notes = str(payment_terms_days) if payment_terms_days != 14 else ""
        payment_terms_days = client_whatsapp
        client_whatsapp = ""

    c_name = str(client_name or "").strip()
    c_email = str(client_email or "").strip()
    c_whatsapp = str(client_whatsapp or "").strip()
    c_notes = str(notes or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        terms_val = max(1, int(payment_terms_days))
    except (ValueError, TypeError):
        terms_val = 14
        
    cursor.execute('''
        INSERT INTO clients (user_id, client_name, client_email, client_whatsapp, payment_terms_days, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, c_name, c_email, c_whatsapp, terms_val, c_notes))
    client_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    sync_to_firestore("clients", client_id, {
        "id": client_id, "user_id": user_id, "client_name": c_name,
        "client_email": c_email, "client_whatsapp": c_whatsapp, "payment_terms_days": terms_val, "notes": c_notes
    })
    
    return client_id


def get_user_clients(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE user_id = ? ORDER BY client_name ASC", (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def delete_client(client_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, user_id))
    conn.commit()
    conn.close()
    
    # Optional: Delete from firestore if we want complete sync.
    # We will just remove from SQLite for now, but to be robust:
    try:
        from google.cloud import firestore
        import os
        project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project_id) if project_id else firestore.Client()
        db.collection("clients").document(str(client_id)).delete()
    except Exception:
        pass
    
    return True

# -------------------------------------------------------------
# INVOICE HELPERS (USER SCOPED)
# -------------------------------------------------------------
def get_next_invoice_number(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT invoice_number FROM invoices WHERE user_id = ? ORDER BY id DESC LIMIT 100", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    max_num = 0
    for row in rows:
        num_str = row["invoice_number"]
        if num_str.startswith("INV-"):
            try:
                num = int(num_str.split("INV-")[1])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
                
    next_num = max_num + 1
    return f"INV-{next_num:03d}"

def create_invoice(user_id, client_name, client_email, invoice_date, due_date, tax_rate, notes, items):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Auto-register client in clients table if not already present
    if client_name and client_name.strip():
        c_name = client_name.strip()
        cursor.execute("SELECT id FROM clients WHERE user_id = ? AND LOWER(client_name) = ?", (user_id, c_name.lower()))
        if not cursor.fetchone():
            c_email = client_email.strip() if client_email else ""
            cursor.execute('''
                INSERT INTO clients (user_id, client_name, client_email, payment_terms_days, notes)
                VALUES (?, ?, ?, 14, 'Auto-registered from invoice')
            ''', (user_id, c_name, c_email))
            c_id = cursor.lastrowid
            sync_to_firestore("clients", c_id, {
                "id": c_id, "user_id": user_id, "client_name": c_name,
                "client_email": c_email, "payment_terms_days": 14, "notes": "Auto-registered from invoice"
            })
    
    invoice_number = get_next_invoice_number(user_id)
    
    tax_rate_clean = max(0.0, float(tax_rate or 0))
    subtotal = sum(max(0.0, float(item["hours"])) * max(0.0, float(item["hourly_rate"])) for item in items)
    tax_amount = subtotal * (tax_rate_clean / 100.0)
    grand_total = subtotal + tax_amount
    
    cursor.execute('''
        INSERT INTO invoices (user_id, invoice_number, client_name, client_email, invoice_date, due_date, tax_rate, subtotal, grand_total, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
    ''', (user_id, invoice_number, client_name, client_email, invoice_date, due_date, tax_rate_clean, subtotal, grand_total, notes))
    
    invoice_id = cursor.lastrowid
    
    for item in items:
        hours = max(0.0, float(item["hours"]))
        rate = max(0.0, float(item["hourly_rate"]))
        amount = hours * rate
        cursor.execute('''
            INSERT INTO invoice_items (invoice_id, description, hours, hourly_rate, amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (invoice_id, item["description"], hours, rate, amount))
        
    conn.commit()
    conn.close()
    
    sync_to_firestore("invoices", invoice_id, {
        "id": invoice_id, "user_id": user_id, "invoice_number": invoice_number,
        "client_name": client_name, "client_email": client_email,
        "invoice_date": invoice_date, "due_date": due_date,
        "tax_rate": float(tax_rate or 0), "subtotal": subtotal, "grand_total": grand_total,
        "notes": notes, "status": "PENDING", "items": items
    })
    
    return get_invoice_by_id(invoice_id, user_id)

def get_all_invoices(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE user_id = ? ORDER BY id DESC", (user_id,))
    invoices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return invoices

def get_invoice_by_id(invoice_id, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM invoices WHERE id = ? AND user_id = ?", (invoice_id, user_id))
    else:
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    inv_row = cursor.fetchone()
    if not inv_row:
        conn.close()
        return None
    invoice = dict(inv_row)
    
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    items = [dict(item) for item in cursor.fetchall()]
    invoice["items"] = items
    conn.close()
    return invoice

def mark_invoice_paid(invoice_id, user_id, payment_date=None):
    if not payment_date:
        payment_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE invoices
        SET status = 'PAID', payment_date = ?
        WHERE id = ? AND user_id = ?
    ''', (payment_date, invoice_id, user_id))
    conn.commit()
    conn.close()

def get_client_history(user_id, client_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM invoices WHERE user_id = ? AND client_name = ?
    ''', (user_id, client_name))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    total_invoices = len(rows)
    paid_invoices = [r for r in rows if r["status"] == "PAID"]
    pending_invoices = [r for r in rows if r["status"] == "PENDING"]
    
    late_count = 0
    total_delay_days = 0
    
    for inv in paid_invoices:
        if inv["payment_date"] and inv["due_date"]:
            try:
                p_date = datetime.strptime(inv["payment_date"], "%Y-%m-%d")
                d_date = datetime.strptime(inv["due_date"], "%Y-%m-%d")
                if p_date > d_date:
                    late_count += 1
                    delay = (p_date - d_date).days
                    total_delay_days += delay
            except ValueError:
                pass
                
    avg_delay_days = round(total_delay_days / late_count, 1) if late_count > 0 else 0
    late_ratio = (late_count / len(paid_invoices)) if paid_invoices else 0.0
    outstanding_amount = sum(r["grand_total"] for r in pending_invoices)
    avg_invoice_amount = (sum(r["grand_total"] for r in rows) / total_invoices) if total_invoices > 0 else 0.0
    
    return {
        "client_name": client_name,
        "total_invoices": total_invoices,
        "paid_invoices_count": len(paid_invoices),
        "late_invoices_count": late_count,
        "late_payment_ratio": round(late_ratio, 2),
        "avg_delay_days": avg_delay_days,
        "outstanding_amount": round(outstanding_amount, 2),
        "avg_invoice_amount": round(avg_invoice_amount, 2)
    }



def create_service(user_id, title, hourly_rate, description=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO services (user_id, title, hourly_rate, description)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title.strip(), float(hourly_rate), description.strip() if description else ""))
    conn.commit()
    service_id = cursor.lastrowid
    conn.close()
    
    srv_data = {"id": service_id, "user_id": user_id, "title": title, "hourly_rate": float(hourly_rate), "description": description}
    sync_to_firestore("services", service_id, srv_data)
    
    return srv_data

def get_user_services(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services WHERE user_id = ? ORDER BY title ASC", (user_id,))
    services = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return services

def update_service(service_id, user_id, title, hourly_rate, description=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE services
        SET title = ?, hourly_rate = ?, description = ?
        WHERE id = ? AND user_id = ?
    ''', (title.strip(), float(hourly_rate), description.strip() if description else "", service_id, user_id))
    conn.commit()
    conn.close()
    return True

def delete_service(service_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = ? AND user_id = ?", (service_id, user_id))
    conn.commit()
    conn.close()
    return True

def update_invoice_pdf_url(invoice_id, user_id, pdf_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE invoices
        SET pdf_url = ?
        WHERE id = ? AND user_id = ?
    ''', (pdf_url, invoice_id, user_id))
    conn.commit()
    conn.close()
    
    # Sync update to Firestore
    sync_to_firestore("invoices", invoice_id, {"pdf_url": pdf_url})
    return True
