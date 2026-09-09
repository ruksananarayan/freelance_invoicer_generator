from flask import Flask, render_template, request, jsonify, session, send_file
from datetime import datetime
import os
import logging

from database import (
    init_db,
    create_user,
    verify_user,
    get_user_by_id,
    create_client,
    get_user_clients,
    get_next_invoice_number,
    create_invoice,
    get_all_invoices,
    get_invoice_by_id,
    mark_invoice_paid,
    get_client_history,
    create_service,
    get_user_services,
    update_service,
    delete_service,
    update_invoice_pdf_url,
    delete_client
)
from risk_engine import calculate_invoice_risk
from gcs_helper import upload_pdf_to_gcs, download_pdf_from_gcs

# Initialize Flask application
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "cts_invoice_risk_guard_secret_key_2026")

# Configure Cloud Logging if running on GCP / Cloud Run
if os.environ.get("K_SERVICE"):
    try:
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()
        logging.info("GCP Cloud Logging initialized successfully.")
    except Exception as e:
        logging.warning(f"Cloud Logging setup deferred: {e}")

# Ensure database tables exist
init_db()

def get_current_user_id():
    return session.get("user_id")

# -------------------------------------------------------------
# PAGE ROUTES
# -------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/invoice/<int:invoice_id>")
def invoice_view_page(invoice_id):
    user_id = get_current_user_id()
    if not user_id:
        return render_template("index.html")
    inv = get_invoice_by_id(invoice_id, user_id)
    return render_template("invoice.html", invoice=inv)

# -------------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# -------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    if not name or not email or not password:
        return jsonify({"error": "Full Name, Email, and Password are required."}), 400
        
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
        
    import re
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return jsonify({"error": "Password must contain both letters and numbers."}), 400
        
    user = create_user(name, email, password)
    if not user:
        return jsonify({"error": "An account with this email already exists."}), 400
        
    session["user_id"] = user["id"]
    return jsonify({"message": "Account registered successfully!", "user": user})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    if not email or not password:
        return jsonify({"error": "Email and Password are required."}), 400
        
    user = verify_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
        
    session["user_id"] = user["id"]
    return jsonify({"message": "Logged in successfully!", "user": user})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully."})

@app.route("/api/auth/me", methods=["GET"])
def get_me():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"authenticated": False}), 200
        
    user = get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"authenticated": False}), 200
        
    return jsonify({"authenticated": True, "user": user})

# -------------------------------------------------------------
# CLIENT ROSTER ENDPOINTS
# -------------------------------------------------------------
@app.route("/api/registered-clients", methods=["GET"])
def list_registered_clients():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    clients = get_user_clients(user_id)
    return jsonify(clients)

@app.route("/api/registered-clients", methods=["POST"])
def add_registered_client():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json(silent=True, force=True) or {}
    name = data.get("client_name", "").strip()
    email = data.get("client_email", "").strip()
    whatsapp = data.get("client_whatsapp", "").strip()
    terms = data.get("payment_terms_days", 14)
    notes = data.get("notes", "").strip()
    
    if not name:
        return jsonify({"error": "Client Name is required."}), 400
        
    client_id = create_client(user_id, name, email, whatsapp, terms, notes)
    return jsonify({"message": f"Client '{name}' registered successfully!", "client_id": client_id}), 201

@app.route("/api/registered-clients/<int:client_id>", methods=["DELETE"])
def delete_client_route(client_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    delete_client(client_id, user_id)
    return jsonify({"message": "Client removed from roster."})

# -------------------------------------------------------------
# FREELANCER WORK & SERVICES CATALOG ENDPOINTS
# -------------------------------------------------------------
@app.route("/api/services", methods=["GET"])
def list_services():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    services = get_user_services(user_id)
    return jsonify(services)

@app.route("/api/services", methods=["POST"])
def add_service():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json or {}
    title = data.get("title", "").strip()
    rate = data.get("hourly_rate", 0)
    desc = data.get("description", "").strip()
    
    if not title:
        return jsonify({"error": "Work/Service Title is required."}), 400
    try:
        rate = float(rate)
        if rate < 0:
            return jsonify({"error": "Hourly rate cannot be negative."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid hourly rate value."}), 400
        
    service = create_service(user_id, title, rate, desc)
    return jsonify({"message": f"Work item '{title}' added to catalog!", "service": service}), 201

@app.route("/api/services/<int:service_id>", methods=["PUT"])
def update_service_route(service_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json or {}
    title = data.get("title", "").strip()
    rate = data.get("hourly_rate", 0)
    desc = data.get("description", "").strip()
    
    if not title:
        return jsonify({"error": "Work/Service Title is required."}), 400
    try:
        rate = float(rate)
        if rate < 0:
            return jsonify({"error": "Hourly rate cannot be negative."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid hourly rate value."}), 400
        
    update_service(service_id, user_id, title, rate, desc)
    return jsonify({"message": "Service updated successfully!"})

@app.route("/api/services/<int:service_id>", methods=["DELETE"])
def delete_service_route(service_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    delete_service(service_id, user_id)
    return jsonify({"message": "Service removed from catalog."})

# -------------------------------------------------------------
# DASHBOARD & INVOICE ENDPOINTS (USER SCOPED)
# -------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_stats():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    invoices = get_all_invoices(user_id)
    
    total_billed = sum(inv["grand_total"] for inv in invoices)
    pending_invoices = [inv for inv in invoices if inv["status"] == "PENDING"]
    paid_invoices = [inv for inv in invoices if inv["status"] == "PAID"]
    
    total_pending = sum(inv["grand_total"] for inv in pending_invoices)
    
    total_overdue = 0.0
    high_risk_count = 0
    overdue_count = 0
    
    for inv in pending_invoices:
        c_history = get_client_history(user_id, inv["client_name"])
        risk = calculate_invoice_risk(inv, c_history)
        if risk["is_overdue"]:
            total_overdue += inv["grand_total"]
            overdue_count += 1
        if risk["risk_level"] == "High":
            high_risk_count += 1
            
    return jsonify({
        "total_invoices": len(invoices),
        "total_billed": round(total_billed, 2),
        "total_pending": round(total_pending, 2),
        "total_overdue": round(total_overdue, 2),
        "overdue_count": overdue_count,
        "high_risk_count": high_risk_count,
        "paid_count": len(paid_invoices),
        "pending_count": len(pending_invoices)
    })

@app.route("/api/invoices", methods=["GET"])
def list_invoices():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    raw_invoices = get_all_invoices(user_id)
    enriched = []
    
    status_filter = request.args.get("status")
    risk_filter = request.args.get("risk")
    search = request.args.get("search", "").strip().lower()
    
    for inv in raw_invoices:
        c_history = get_client_history(user_id, inv["client_name"])
        risk = calculate_invoice_risk(inv, c_history)
        
        item = {
            **inv,
            "risk": risk,
            "client_history": c_history
        }
        
        if search:
            match_name = search in inv["client_name"].lower()
            match_num = search in inv["invoice_number"].lower()
            if not (match_name or match_num):
                continue
                
        if status_filter:
            if status_filter == "OVERDUE" and not risk["is_overdue"]:
                continue
            elif status_filter == "PENDING" and inv["status"] != "PENDING":
                continue
            elif status_filter == "PAID" and inv["status"] != "PAID":
                continue

        if risk_filter and risk["risk_level"].upper() != risk_filter.upper():
            continue
            
        enriched.append(item)
        
    return jsonify(enriched)

@app.route("/api/invoices/next-number", methods=["GET"])
def fetch_next_number():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    next_num = get_next_invoice_number(user_id)
    return jsonify({"next_invoice_number": next_num})

@app.route("/api/invoices", methods=["POST"])
def add_invoice():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json or {}
    client_name = data.get("client_name", "").strip()
    client_email = data.get("client_email", "").strip()
    invoice_date = data.get("invoice_date", "").strip()
    due_date = data.get("due_date", "").strip()
    tax_rate = data.get("tax_rate", 0)
    notes = data.get("notes", "").strip()
    items = data.get("items", [])
    
    if not client_name or not invoice_date or not due_date:
        return jsonify({"error": "Client Name, Invoice Date, and Due Date are required fields."}), 400

    try:
        datetime.strptime(invoice_date, "%Y-%m-%d")
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400
        
    if not items or len(items) == 0:
        return jsonify({"error": "At least one line item is required."}), 400
        
    for item in items:
        if not item.get("description") or float(item.get("hours", 0)) <= 0 or float(item.get("hourly_rate", 0)) <= 0:
            return jsonify({"error": "Each line item must have a description, positive hours, and hourly rate."}), 400

    created_inv = create_invoice(
        user_id=user_id,
        client_name=client_name,
        client_email=client_email,
        invoice_date=invoice_date,
        due_date=due_date,
        tax_rate=tax_rate,
        notes=notes,
        items=items
    )
    
    c_history = get_client_history(user_id, client_name)
    risk = calculate_invoice_risk(created_inv, c_history)
    inv_number = created_inv["invoice_number"]
    
    return jsonify({
        "message": f"Invoice {inv_number} created successfully!",
        "invoice": {
            **created_inv,
            "risk": risk
        }
    }), 201

@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
def get_invoice_detail(invoice_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    inv = get_invoice_by_id(invoice_id, user_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
        
    c_history = get_client_history(user_id, inv["client_name"])
    risk = calculate_invoice_risk(inv, c_history)
    
    return jsonify({
        **inv,
        "risk": risk,
        "client_history": c_history
    })

@app.route("/api/invoices/<int:invoice_id>/mark-paid", methods=["POST"])
def update_invoice_to_paid(invoice_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    inv = get_invoice_by_id(invoice_id, user_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
        
    data = request.get_json(silent=True) or {}
    pay_date = data.get("payment_date")
    mark_invoice_paid(invoice_id, user_id, pay_date)
    
    updated = get_invoice_by_id(invoice_id, user_id)
    return jsonify({
        "message": f"Invoice {updated['invoice_number']} marked as PAID.",
        "invoice": updated
    })

@app.route("/api/invoices/<int:invoice_id>/upload-pdf", methods=["POST"])
def upload_invoice_pdf(invoice_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    inv = get_invoice_by_id(invoice_id, user_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
        
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400
        
    pdf_file = request.files["pdf"]
    pdf_bytes = pdf_file.read()
    filename = f"{invoice_id}_{pdf_file.filename}"
    
    # Upload to GCS Bucket
    pdf_url = upload_pdf_to_gcs(pdf_bytes, filename)
    if pdf_url:
        update_invoice_pdf_url(invoice_id, user_id, pdf_url)
        return jsonify({"message": "PDF uploaded successfully", "pdf_url": pdf_url}), 200
    else:
        return jsonify({"error": "Failed to upload PDF to Google Cloud Storage"}), 500

@app.route("/api/invoices/<int:invoice_id>/download-pdf", methods=["GET"])
def download_invoice_pdf(invoice_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    inv = get_invoice_by_id(invoice_id, user_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
        
    filename = f"{invoice_id}_{inv['invoice_number']}.pdf"
    
    # Download privately from GCS
    pdf_bytes = download_pdf_from_gcs(filename)
    if pdf_bytes:
        import io
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"{inv['invoice_number']}.pdf"
        )
    else:
        return jsonify({"error": "PDF not found in cloud storage"}), 404

@app.route("/public/invoices/<int:invoice_id>/download-pdf", methods=["GET"])
def public_download_invoice_pdf(invoice_id):
    # No auth check here so clients can download via WhatsApp link
    inv = get_invoice_by_id(invoice_id, user_id=None)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
        
    filename = f"{invoice_id}_{inv['invoice_number']}.pdf"
    
    # Download privately from GCS
    pdf_bytes = download_pdf_from_gcs(filename)
    if pdf_bytes:
        import io
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"{inv['invoice_number']}.pdf"
        )
    else:
        return jsonify({"error": "PDF not found in cloud storage"}), 404

@app.route("/api/clients", methods=["GET"])
def get_clients_summary():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    invoices = get_all_invoices(user_id)
    client_names = list(set(inv["client_name"] for inv in invoices))
    
    clients = []
    for name in client_names:
        history = get_client_history(user_id, name)
        clients.append(history)
        
    return jsonify(clients)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
