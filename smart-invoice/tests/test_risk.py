import unittest
from datetime import date, timedelta
import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from risk_engine import calculate_invoice_risk
from database import init_db, get_next_invoice_number

class TestSmartInvoice(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_overdue_high_risk_calculation(self):
        today = date.today().strftime("%Y-%m-%d")
        due_10_days_ago = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        invoice = {
            "due_date": due_10_days_ago,
            "grand_total": 4500.0,
            "status": "PENDING"
        }
        
        client_history = {
            "client_name": "Risk Corp",
            "total_invoices": 5,
            "paid_invoices_count": 4,
            "late_invoices_count": 3,
            "late_payment_ratio": 0.75,
            "avg_delay_days": 8.5,
            "outstanding_amount": 4500.0,
            "avg_invoice_amount": 2000.0
        }
        
        risk = calculate_invoice_risk(invoice, client_history, current_date_str=today)
        self.assertTrue(risk["is_overdue"])
        self.assertEqual(risk["days_diff"], 10)
        self.assertGreaterEqual(risk["risk_score"], 70)
        self.assertEqual(risk["risk_level"], "High")

    def test_punctual_client_low_risk(self):
        today = date.today().strftime("%Y-%m-%d")
        due_5_days_ahead = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        
        invoice = {
            "due_date": due_5_days_ahead,
            "grand_total": 1200.0,
            "status": "PENDING"
        }
        
        client_history = {
            "client_name": "Punctual Tech",
            "total_invoices": 10,
            "paid_invoices_count": 10,
            "late_invoices_count": 0,
            "late_payment_ratio": 0.0,
            "avg_delay_days": 0.0,
            "outstanding_amount": 1200.0,
            "avg_invoice_amount": 1500.0
        }
        
        risk = calculate_invoice_risk(invoice, client_history, current_date_str=today)
        self.assertFalse(risk["is_overdue"])
        self.assertEqual(risk["risk_level"], "Low")

    def test_sequential_numbering(self):
        num = get_next_invoice_number(user_id=1)
        self.assertTrue(num.startswith("INV-"))

    def test_user_authentication_plain_password_and_double_hash_protection(self):
        from database import create_user, verify_user
        from database.database import get_db_connection
        import time
        email = f"auth_test_{int(time.time())}@example.com"
        plain_pwd = "MySecretPass123"

        # 1. Create User
        u = create_user("Test User", email, plain_pwd)
        self.assertIsNotNone(u)

        # 2. Login with plain text password should succeed
        logged_in = verify_user(email, plain_pwd)
        self.assertIsNotNone(logged_in)
        self.assertEqual(logged_in["email"], email)

        # 3. Get stored hash from DB
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        stored_hash = c.fetchone()["password_hash"]
        conn.close()

        # 4. Attempting to log in using the ENCRYPTED HASH as password should fail and NOT corrupt stored hash
        bad_login = verify_user(email, stored_hash)
        self.assertIsNone(bad_login)

        # 5. Confirm stored hash in DB was NOT changed/double-hashed
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        hash_after = c.fetchone()["password_hash"]
        conn.close()
        self.assertEqual(stored_hash, hash_after)

        # 6. Logging in again with original plain text password must still succeed
        relocked = verify_user(email, plain_pwd)
        self.assertIsNotNone(relocked)

if __name__ == "__main__":
    unittest.main()

