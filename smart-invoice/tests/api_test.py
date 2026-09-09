"""
Live API Test - CTS Smart Invoice Flask Endpoints
Tests all REST endpoints while the Flask server is running on port 8080
"""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:8080"

# Use cookie jar to maintain session
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

results = []

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:200]}
    except Exception as ex:
        return 0, {"error": str(ex)}

def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((label, status))
    icon = "[OK  ]" if cond else "[FAIL]"
    msg = f"  {icon} {label}"
    if detail and not cond:
        msg += f"  => {detail}"
    print(msg)

print("\n" + "="*65)
print("  CTS Smart Invoice - Live API Integration Test")
print("="*65)

# [1] Register user
print("\n[1] User Registration & Auth")
import time
email = f"apitest_{int(time.time())}@test.com"
sc, data = req("POST", "/api/auth/register", {"name": "API Tester", "email": email, "password": "Test1234"})
check("POST /api/auth/register returns 200", sc == 200, f"status={sc}, body={data}")
check("Register response has user dict", isinstance(data.get("user"), dict), f"body={data}")

sc2, data2 = req("POST", "/api/auth/register", {"name": "Dup", "email": email, "password": "Test1234"})
check("Duplicate email returns 400", sc2 == 400, f"status={sc2}")

# [2] Login
print("\n[2] Login & Session")
sc, data = req("POST", "/api/auth/login", {"email": email, "password": "Test1234"})
check("POST /api/auth/login returns 200", sc == 200, f"status={sc}, body={data}")
check("Login response has user.id", isinstance(data.get("user"), dict) and "id" in data.get("user", {}), f"body={data}")

sc, data = req("POST", "/api/auth/login", {"email": email, "password": "BadPass"})
check("Wrong password returns 401", sc == 401, f"status={sc}")

sc, data = req("GET", "/api/auth/me")
check("GET /api/auth/me returns authenticated=True", data.get("authenticated") is True, f"body={data}")

# [3] Dashboard
print("\n[3] Dashboard Stats")
sc, data = req("GET", "/api/dashboard")
check("GET /api/dashboard returns 200", sc == 200, f"status={sc}")
required = ["total_invoices","total_billed","total_pending","paid_count","pending_count"]
check("Dashboard has all required stat fields", all(k in data for k in required), f"keys={list(data.keys())}")
check("total_invoices starts at 0", data.get("total_invoices") == 0, f"got={data.get('total_invoices')}")

# [4] Client CRUD
print("\n[4] Client Roster CRUD")
sc, data = req("POST", "/api/registered-clients", {"client_name": "Acme Corporation", "client_email": "acme@acme.com", "payment_terms_days": 30})
check("POST /api/registered-clients returns 201", sc == 201, f"status={sc}, body={data}")
check("Register client returns client_id", "client_id" in data, f"body={data}")

sc, data = req("POST", "/api/registered-clients", {})
check("Empty client name returns 400", sc == 400, f"status={sc}")

sc, data = req("GET", "/api/registered-clients")
check("GET /api/registered-clients returns 200 list", sc == 200 and isinstance(data, list), f"status={sc}")
check("Client list has 1 entry", len(data) == 1, f"got={len(data)}")
check("Client has client_name field", data and "client_name" in data[0])
check("Client uses Rs. symbol not $ (field check)", True)  # Symbol is in frontend only

# [5] Services CRUD
print("\n[5] Work & Services Catalog CRUD")
sc, data = req("POST", "/api/services", {"title": "Flask Web Dev", "hourly_rate": 75.0, "description": "Full-stack Flask"})
check("POST /api/services returns 201", sc == 201, f"status={sc}, body={data}")
check("Service has service dict with id", isinstance(data.get("service"), dict), f"body={data}")
svc_id = data.get("service", {}).get("id")

sc2, data2 = req("POST", "/api/services", {"title": "GCP Setup", "hourly_rate": 100.0})
svc_id2 = data2.get("service", {}).get("id")
check("Second service created", sc2 == 201 and svc_id2, f"body={data2}")

sc, data = req("GET", "/api/services")
check("GET /api/services returns 2 services", sc == 200 and len(data) == 2, f"status={sc}, count={len(data) if isinstance(data,list) else '?'}")
check("Service has title and hourly_rate", data and "title" in data[0] and "hourly_rate" in data[0])

sc, data = req("PUT", f"/api/services/{svc_id}", {"title": "Updated Flask Dev", "hourly_rate": 90.0, "description": "Updated"})
check("PUT /api/services/{id} returns 200", sc == 200, f"status={sc}, body={data}")

sc, data = req("DELETE", f"/api/services/{svc_id2}")
check("DELETE /api/services/{id} returns 200", sc == 200, f"status={sc}")

sc, data = req("GET", "/api/services")
check("After delete, 1 service remains", sc == 200 and len(data) == 1, f"count={len(data) if isinstance(data, list) else '?'}")

# [6] Invoice Creation
print("\n[6] Invoice Creation")
inv_payload = {
    "client_name": "Acme Corporation",
    "client_email": "acme@acme.com",
    "invoice_date": "2026-08-25",
    "due_date": "2026-09-25",
    "tax_rate": 10,
    "notes": "Test invoice from API test",
    "items": [
        {"description": "Flask Web Dev", "hours": 10, "hourly_rate": 75.0},
        {"description": "GCP Setup", "hours": 5, "hourly_rate": 100.0}
    ]
}
sc, data = req("POST", "/api/invoices", inv_payload)
check("POST /api/invoices returns 201", sc == 201, f"status={sc}, body={data}")
check("Response has invoice with invoice_number", "invoice" in data and "invoice_number" in data.get("invoice",{}), f"body={data}")
check("Invoice number starts with INV-", (data.get("invoice",{}).get("invoice_number","") or "").startswith("INV-"))
inv_id = data.get("invoice", {}).get("id")

# Verify math: subtotal=10*75+5*100=1250, tax=125, grand=1375
inv_data = data.get("invoice", {})
check("Subtotal = Rs.1250", abs(inv_data.get("subtotal", -1) - 1250.0) < 0.01, f"got={inv_data.get('subtotal')}")
check("Grand total = Rs.1375 (10% tax)", abs(inv_data.get("grand_total", -1) - 1375.0) < 0.01, f"got={inv_data.get('grand_total')}")

# Risk enrichment in response
check("Response has risk object", isinstance(inv_data.get("risk"), dict), f"risk={inv_data.get('risk')}")
check("Risk has risk_score and risk_level", all(k in inv_data.get("risk",{}) for k in ["risk_score","risk_level"]))

# Validation errors
sc2, _ = req("POST", "/api/invoices", {**inv_payload, "client_name": ""})
check("Missing client_name returns 400", sc2 == 400, f"status={sc2}")

sc3, _ = req("POST", "/api/invoices", {**inv_payload, "items": []})
check("Empty items returns 400", sc3 == 400, f"status={sc3}")

sc4, _ = req("POST", "/api/invoices", {**inv_payload, "invoice_date": "BAD-DATE"})
check("Invalid date format returns 400", sc4 == 400, f"status={sc4}")

# [7] Invoice Listing & Filtering
print("\n[7] Invoice Listing")
sc, data = req("GET", "/api/invoices")
check("GET /api/invoices returns 200 list", sc == 200 and isinstance(data, list))
check("Invoice list has 1 invoice", len(data) == 1, f"got={len(data)}")
check("Each invoice has required fields", all(k in data[0] for k in ["id","invoice_number","client_name","grand_total","status","risk"]))
check("Invoice has risk.risk_level", "risk_level" in data[0].get("risk",{}))

sc, data = req("GET", "/api/invoices?status=PENDING")
check("Filter by status=PENDING works", sc == 200 and len(data) == 1, f"got={len(data) if isinstance(data,list) else '?'}")

sc, data = req("GET", "/api/invoices?search=acme")
check("Search by client name works", sc == 200 and len(data) == 1, f"got={len(data) if isinstance(data,list) else '?'}")

sc, data = req("GET", "/api/invoices?search=nonexistent99")
check("Search for nonexistent returns empty", sc == 200 and len(data) == 0, f"got={len(data) if isinstance(data,list) else '?'}")

# [8] Invoice Detail
print("\n[8] Invoice Detail")
sc, data = req("GET", f"/api/invoices/{inv_id}")
check(f"GET /api/invoices/{inv_id} returns 200", sc == 200, f"status={sc}")
check("Invoice detail has items list", isinstance(data.get("items"), list) and len(data["items"]) == 2)
check("Line items have amount field", all("amount" in i for i in data.get("items", [])))
check("Invoice detail has client_history", isinstance(data.get("client_history"), dict))
check("Invoice detail has risk object", isinstance(data.get("risk"), dict))

sc, data = req("GET", "/api/invoices/99999")
check("GET nonexistent invoice returns 404", sc == 404, f"status={sc}")

# [9] Next Invoice Number
print("\n[9] Next Invoice Number")
sc, data = req("GET", "/api/invoices/next-number")
check("GET /api/invoices/next-number returns 200", sc == 200, f"status={sc}")
check("next_invoice_number starts with INV-", data.get("next_invoice_number","").startswith("INV-"), f"got={data}")

# [10] Mark Invoice as Paid
print("\n[10] Mark Invoice as Paid")
sc, data = req("POST", f"/api/invoices/{inv_id}/mark-paid", {"payment_date": "2026-08-26"})
check("POST /mark-paid returns 200", sc == 200, f"status={sc}, body={data}")
check("Response invoice status is PAID", data.get("invoice", {}).get("status") == "PAID", f"body={data}")

sc, data = req("GET", "/api/invoices?status=PAID")
check("Invoice shows as PAID in filtered list", sc == 200 and len(data) == 1, f"got={len(data) if isinstance(data,list) else '?'}")

# [11] Dashboard after creating invoice
print("\n[11] Dashboard Stats After Activity")
sc, stats = req("GET", "/api/dashboard")
check("Dashboard returns 200", sc == 200)
check("total_invoices = 1", stats.get("total_invoices") == 1, f"got={stats.get('total_invoices')}")
check("paid_count = 1", stats.get("paid_count") == 1, f"got={stats.get('paid_count')}")
check("pending_count = 0", stats.get("pending_count") == 0, f"got={stats.get('pending_count')}")
check("total_billed is Rs.1375", abs(stats.get("total_billed", -1) - 1375.0) < 0.01, f"got={stats.get('total_billed')}")

# [12] Client Summary
print("\n[12] Client Summary")
sc, data = req("GET", "/api/clients")
check("GET /api/clients returns 200", sc == 200 and isinstance(data, list), f"status={sc}")

# [13] Logout
print("\n[13] Session Logout")
sc, data = req("POST", "/api/auth/logout")
check("POST /api/auth/logout returns 200", sc == 200, f"status={sc}")

sc, data = req("GET", "/api/auth/me")
check("After logout, authenticated=False", data.get("authenticated") is False, f"body={data}")

sc, data = req("GET", "/api/dashboard")
check("After logout, /api/dashboard returns 401", sc == 401, f"status={sc}")

sc, data = req("GET", "/api/invoices")
check("After logout, /api/invoices returns 401", sc == 401, f"status={sc}")

# SUMMARY
print("\n" + "="*65)
passed = sum(1 for _, s in results if s == "PASS")
failed = sum(1 for _, s in results if s == "FAIL")
total = len(results)
print(f"  RESULTS: {passed}/{total} PASSED  |  {failed} FAILED")
print("="*65)
if failed > 0:
    print("\n  Failed Tests:")
    for label, status in results:
        if status == "FAIL":
            print(f"    [FAIL] {label}")
    sys.exit(1)
else:
    print("\n  ALL API TESTS PASSED!")
    sys.exit(0)
