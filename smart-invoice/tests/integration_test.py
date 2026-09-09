"""
Full Integration Test Suite - CTS Smart Invoice & Risk Guard
Tests: User Registration, Login, Client CRUD, Service CRUD, Invoice CRUD, Risk Engine

Return type reference (from database.py):
  create_user()    -> dict {id, name, email, created_at} or None on duplicate
  verify_user()    -> dict {id, name, email} or None
  get_user_by_id() -> dict {id, name, email} or None
  create_client()  -> integer client_id
  get_user_clients()-> list of dicts
  create_service() -> dict {id, user_id, title, hourly_rate, description}
  create_invoice() -> full invoice dict (with items, subtotal, grand_total, status)
  get_all_invoices()-> list of dicts
  get_invoice_by_id()-> dict or None
  mark_invoice_paid() -> True
  get_client_history()-> dict
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import (
    init_db, create_user, verify_user, get_user_by_id,
    create_client, get_user_clients,
    create_service, get_user_services, update_service, delete_service,
    create_invoice, get_all_invoices, get_invoice_by_id,
    get_client_history, mark_invoice_paid, get_next_invoice_number
)
from risk_engine.risk import calculate_invoice_risk

results = []

def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((label, status, detail))
    icon = "[OK  ]" if cond else "[FAIL]"
    msg = f"  {icon} {label}"
    if detail and not cond:
        msg += f"  => {detail}"
    print(msg)

print("\n" + "="*65)
print("  CTS Smart Invoice & Risk Guard - Full Integration Test Suite")
print("="*65)

# ============================================================
# [1] DATABASE INITIALIZATION
# ============================================================
print("\n[1] Database Initialization")
init_db()
check("Database initialized without error", True)

# ============================================================
# [2] USER REGISTRATION & AUTH
# ============================================================
print("\n[2] User Registration & Authentication")
unique_email = f"tester_{int(time.time())}@test.com"

# create_user returns dict or None
user_created = create_user("Test Freelancer", unique_email, "SecurePass123!")
check("create_user() returns a dict", isinstance(user_created, dict), f"got type: {type(user_created)}")
check("Returned dict has 'id' key > 0", isinstance(user_created, dict) and user_created.get("id", 0) > 0, f"got: {user_created}")
uid = user_created["id"] if isinstance(user_created, dict) else None

# verify_user correct password
user = verify_user(unique_email, "SecurePass123!")
check("Correct password login returns user dict", user is not None and "id" in user)
check("Logged-in user ID matches created ID", user is not None and user["id"] == uid)
check("User name returned correctly", user is not None and user["name"] == "Test Freelancer")

# verify_user wrong password
bad = verify_user(unique_email, "WrongPassword!")
check("Wrong password returns None", bad is None, f"got: {bad}")

# get_user_by_id
uobj = get_user_by_id(uid)
check("get_user_by_id returns correct email", uobj is not None and uobj["email"] == unique_email)

# Duplicate registration
dup = create_user("Test Freelancer", unique_email, "SecurePass123!")
check("Duplicate email registration returns None", dup is None, f"got: {dup}")

# ============================================================
# [3] CLIENT REGISTRATION & RETRIEVAL
# ============================================================
print("\n[3] Client Registration & Retrieval")

# create_client returns integer ID
cid1 = create_client(uid, "Acme Corporation", "billing@acme.com", 30, "Top client")
check("create_client() returns positive integer", isinstance(cid1, int) and cid1 > 0, f"got: {cid1}")

cid2 = create_client(uid, "TechCorp India", "tech@techcorp.in", 14, "Second client")
check("Second client created with positive ID", isinstance(cid2, int) and cid2 > 0, f"got: {cid2}")

clients = get_user_clients(uid)
check("get_user_clients returns 2 clients", len(clients) == 2, f"got: {len(clients)}")
check("Client has required fields", all("client_name" in c and "client_email" in c for c in clients))
check("Clients sorted alphabetically", clients[0]["client_name"] == "Acme Corporation", f"got: {[c['client_name'] for c in clients]}")

# ============================================================
# [4] SERVICES CATALOG CRUD
# ============================================================
print("\n[4] Work & Services Catalog (CRUD)")

# create_service returns dict
svc1 = create_service(uid, "Flask Web Development", 75.0, "Full-stack Flask application")
check("create_service() returns a dict", isinstance(svc1, dict), f"got: {type(svc1)}")
check("Service dict has 'id' key > 0", isinstance(svc1, dict) and svc1.get("id", 0) > 0, f"got: {svc1}")
sid1 = svc1["id"] if isinstance(svc1, dict) else None

svc2 = create_service(uid, "GCP Cloud Setup", 100.0, "Cloud Run deployment")
check("Service 2 created with ID", isinstance(svc2, dict) and svc2.get("id", 0) > 0, f"got: {svc2}")
sid2 = svc2["id"] if isinstance(svc2, dict) else None

services = get_user_services(uid)
check("Two services found", len(services) == 2, f"got: {len(services)}")
check("Service rate stored correctly", any(s["hourly_rate"] == 75.0 for s in services))

# Update
update_service(sid1, uid, "Full-Stack Flask Development", 85.0, "Updated description")
updated_svcs = get_user_services(uid)
updated_svc = next((s for s in updated_svcs if s["id"] == sid1), None)
check("Service title updated", updated_svc and updated_svc["title"] == "Full-Stack Flask Development", f"got: {updated_svc}")
check("Service rate updated to 85.0", updated_svc and updated_svc["hourly_rate"] == 85.0, f"got: {updated_svc}")

# Delete
delete_service(sid2, uid)
after_del = get_user_services(uid)
check("Service deleted (1 remains)", len(after_del) == 1, f"got: {len(after_del)}")

# ============================================================
# [5] INVOICE CREATION & AMOUNT CALCULATIONS
# ============================================================
print("\n[5] Invoice Creation & Amount Calculation")

items1 = [
    {"description": "Flask Web Development", "hours": 20, "hourly_rate": 75.0},
    {"description": "GCP Cloud Setup",       "hours":  5, "hourly_rate": 100.0},
]
# create_invoice returns full invoice dict
inv1 = create_invoice(uid, "Acme Corporation", "billing@acme.com", "2026-08-01", "2026-09-30", 10.0, "Invoice 1 notes", items1)
check("create_invoice returns a dict", isinstance(inv1, dict), f"got: {type(inv1)}")
check("Invoice has 'id' and 'invoice_number'", "id" in (inv1 or {}) and "invoice_number" in (inv1 or {}), f"got: {inv1}")
inv_id1 = inv1["id"] if inv1 else None
inv_num1 = inv1["invoice_number"] if inv1 else ""
check("Invoice number format INV-XXX", inv_num1.startswith("INV-"), f"got: {inv_num1}")
check("Invoice status defaults to PENDING", inv1.get("status") == "PENDING", f"got: {inv1.get('status')}")

expected_subtotal = 20*75 + 5*100   # 2000
expected_grand   = 2000 + 2000*0.10  # 2200
check("Subtotal = Rs.2000", abs((inv1 or {}).get("subtotal", -1) - expected_subtotal) < 0.01, f"got: {(inv1 or {}).get('subtotal')}")
check("Grand total = Rs.2200 (10% tax)", abs((inv1 or {}).get("grand_total", -1) - expected_grand) < 0.01, f"got: {(inv1 or {}).get('grand_total')}")

# Check line items
check("Invoice has 2 line items", isinstance(inv1.get("items"), list) and len(inv1["items"]) == 2, f"got: {inv1.get('items')}")
li = inv1["items"][0] if inv1 and inv1.get("items") else {}
check("Line item has required fields", all(k in li for k in ["description","hours","hourly_rate","amount"]))
check("Line item amount correct (20h * Rs.75 = Rs.1500)", abs(li.get("amount", -1) - 1500.0) < 0.01, f"got: {li.get('amount')}")

# ============================================================
# [6] SEQUENTIAL INVOICE NUMBERING
# ============================================================
print("\n[6] Sequential Invoice Numbering")
items2 = [{"description": "Consultation", "hours": 3, "hourly_rate": 120.0}]
inv2 = create_invoice(uid, "TechCorp India", "", "2026-08-10", "2026-08-24", 0, "Second invoice", items2)
inv_id2 = inv2["id"] if inv2 else None
inv_num2 = inv2["invoice_number"] if inv2 else ""

check("Second invoice ID > first", (inv_id2 or 0) > (inv_id1 or 0))
n1 = int(inv_num1.split("-")[1]) if inv_num1 else 0
n2 = int(inv_num2.split("-")[1]) if inv_num2 else 0
check("Invoice numbers sequential (n2 = n1 + 1)", n2 == n1 + 1, f"got: {inv_num1} -> {inv_num2}")

# ============================================================
# [7] AUTO-CLIENT REGISTRATION FROM INVOICE
# ============================================================
print("\n[7] Auto-Client Registration from Invoice")
items3 = [{"description": "Design Work", "hours": 8, "hourly_rate": 60.0}]
inv3 = create_invoice(uid, "Brand New Client Co", "new@client.com", "2026-08-15", "2026-09-15", 0, "", items3)
inv_id3 = inv3["id"] if inv3 else None
all_clients = get_user_clients(uid)
all_client_names = [c["client_name"] for c in all_clients]
check("'Brand New Client Co' auto-registered in clients table", "Brand New Client Co" in all_client_names, f"clients: {all_client_names}")

# ============================================================
# [8] INVOICE RETRIEVAL
# ============================================================
print("\n[8] Invoice Retrieval & List")
all_invoices = get_all_invoices(uid)
check("All 3 invoices retrieved", len(all_invoices) == 3, f"got: {len(all_invoices)}")
check("Ordered newest first", all_invoices[0]["id"] > all_invoices[-1]["id"])
required_fields = ["id","invoice_number","client_name","grand_total","status","due_date"]
check("Each invoice has required fields", all(all(k in inv for k in required_fields) for inv in all_invoices))

inv_detail = get_invoice_by_id(inv_id1, uid)
check("get_invoice_by_id returns correct invoice", inv_detail is not None and inv_detail["id"] == inv_id1)

# ============================================================
# [9] MARK INVOICE AS PAID
# ============================================================
print("\n[9] Mark Invoice as Paid")
mark_invoice_paid(inv_id2, uid)
paid_inv = get_invoice_by_id(inv_id2, uid)
check("Invoice 2 status = PAID", paid_inv.get("status") == "PAID", f"got: {paid_inv.get('status')}")
check("Paid invoice keeps correct grand_total", abs(paid_inv.get("grand_total", -1) - 3*120) < 0.01, f"got: {paid_inv.get('grand_total')}")

# ============================================================
# [10] CLIENT HISTORY
# ============================================================
print("\n[10] Client History Tracking")
acme_hist = get_client_history(uid, "Acme Corporation")
check("Client history returned for Acme", acme_hist is not None)
check("History has required fields", all(k in (acme_hist or {}) for k in ["client_name","total_invoices","late_payment_ratio","paid_invoices_count"]))
check("Acme total_invoices = 1", (acme_hist or {}).get("total_invoices") == 1, f"got: {(acme_hist or {}).get('total_invoices')}")

tech_hist = get_client_history(uid, "TechCorp India")
check("TechCorp paid_invoices_count = 1", (tech_hist or {}).get("paid_invoices_count") == 1, f"got: {tech_hist}")

# ============================================================
# [11] RISK SCORING ENGINE
# ============================================================
print("\n[11] Risk Scoring Engine")

# Scenario A: Overdue + high late-payment history
overdue_inv = {
    "id": 99, "client_name": "BadPayer Ltd",
    "invoice_date": "2026-06-01", "due_date": "2026-06-30",
    "grand_total": 8000.0, "status": "PENDING",
    "notes": "No response, multiple follow-ups sent"
}
bad_hist = {"late_invoices_count": 3, "paid_invoices_count": 1, "total_invoices": 4,
            "late_payment_ratio": 0.75, "avg_delay_days": 20, "outstanding_amount": 8000}
risk_a = calculate_invoice_risk(overdue_inv, bad_hist, current_date_str="2026-08-25")
check("Overdue high-risk score > 50", risk_a["risk_score"] > 50, f"score={risk_a['risk_score']}")
check("Risk level is High or Medium", risk_a["risk_level"] in ["High", "Medium"], f"level={risk_a['risk_level']}")
check("is_overdue=True for past-due invoice", risk_a["is_overdue"] is True)
check("Result has all required keys", all(k in risk_a for k in ["risk_score","risk_level","is_overdue","recommended_action","explanations"]))

# Scenario B: Paid invoice should not score as high
paid_ov = {**overdue_inv, "status": "PAID"}
risk_b = calculate_invoice_risk(paid_ov, bad_hist, current_date_str="2026-08-25")
check("Paid invoice scores <= overdue pending invoice", risk_b["risk_score"] <= risk_a["risk_score"])

# Scenario C: Punctual client, not overdue
good_inv = {
    "id": 100, "client_name": "Punctual Corp",
    "invoice_date": "2026-08-20", "due_date": "2026-09-20",
    "grand_total": 500.0, "status": "PENDING", "notes": "Routine invoice"
}
good_hist = {"late_invoices_count": 0, "paid_invoices_count": 5, "total_invoices": 5,
             "late_payment_ratio": 0.0, "avg_delay_days": 0, "outstanding_amount": 500}
risk_c = calculate_invoice_risk(good_inv, good_hist, current_date_str="2026-08-25")
check("Punctual client scores < 40", risk_c["risk_score"] < 40, f"score={risk_c['risk_score']}")
check("Not overdue (due 2026-09-20)", risk_c["is_overdue"] is False)

# Scenario D: Brand-new client (no history)
new_inv = {"id": 101, "client_name": "First Timer", "invoice_date": "2026-08-24",
           "due_date": "2026-09-30", "grand_total": 1500.0, "status": "PENDING", "notes": ""}
new_hist = {"late_invoices_count": 0, "paid_invoices_count": 0, "total_invoices": 0,
            "late_payment_ratio": 0.0, "avg_delay_days": 0, "outstanding_amount": 1500}
risk_d = calculate_invoice_risk(new_inv, new_hist, current_date_str="2026-08-25")
check("New client score in valid 0-100 range", 0 <= risk_d["risk_score"] <= 100, f"score={risk_d['risk_score']}")
check("New client has a recommended_action", bool(risk_d.get("recommended_action")))

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*65)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total = len(results)
print(f"  RESULTS: {passed}/{total} PASSED  |  {failed} FAILED")
print("="*65)

if failed > 0:
    print("\n  Failed Tests:")
    for label, status, detail in results:
        if status == "FAIL":
            print(f"    [FAIL] {label}")
            if detail:
                print(f"           => {detail}")
    sys.exit(1)
else:
    print("\n  ALL TESTS PASSED - Application is healthy!")
    sys.exit(0)
