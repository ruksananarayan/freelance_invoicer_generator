# Project Rules & Architecture Knowledge Base

This document details established repository patterns, structural requirements, and architectural rules for future development on the Smart Freelance Invoice & Payment Risk System (CTS Invoice Guard).

---

## 🏛️ 1. Database & Persistence Patterns (`database/database.py`)

- **Explicit Transaction Commits**:
  - For SQLite write operations (inserts, updates, deletes), you **must** explicitly call `conn.commit()` before closing the connection. 
  - Functions like `create_client` will fail to persist records on disk without this.
- **Return Type Standardization**:
  - `create_user`, `create_invoice`, and `create_service` **must** return complete dictionary objects representing the newly inserted rows (e.g., `dict(row)`).
  - `create_client` **must** return the integer `client_id` directly (matching the frontend expectations).
- **Schema Migrations**:
  - During database initialization (`init_db()`), always execute dynamic column addition checks (`ALTER TABLE invoices ADD COLUMN pdf_url TEXT`) within a `try-except sqlite3.OperationalError` block to avoid breaking existing developer data setups.

---

## 🔒 2. Cloud Storage PDF Security Flow (GCS Bucket)

- **Bucket Privacy**:
  - To secure user invoicing data and avoid leakage of rates, billing numbers, and names, the Google Cloud Storage bucket (`smart-invoice-pdfs-extreme-gecko-472506-s9`) is configured as **private** (Public Access: Not public).
- **Secure Download Proxy**:
  - Do **not** expose raw GCS URLs to the frontend browser, as they will throw `Access Denied` errors.
  - Instead, route downloads through the Flask proxy route: `GET /api/invoices/<id>/download-pdf`.
  - Flask validates the session ID via cookie authorization (`get_current_user_id()`). If authenticated, it streams the PDF bytes privately using the backend's GCP credentials.

---

## 🧠 3. Payment Risk Engine (`risk_engine/risk.py`)

- **Required Dictionary Keys**:
  - The risk calculator **must** return a dict containing precisely:
    `status_label`, `is_overdue`, `days_diff`, `risk_score`, `risk_level`, `risk_color`, `explanations`, `recommended_action`, and `breakdown`.
  - Do **not** rename `explanations` or `breakdown` to key variants like `risk_drivers` since frontend parsing depends on them.

---

## 🎨 4. Frontend Tab Switcher & Styling Architecture

- **Single-Page View (Tab Panes)**:
  - Keep dashboard analytics and invoicing operations unified in a single page (`index.html`) using tab navigation.
  - `#dashboard-tab-content`: Overview metric cards, inline predefined works, and client roster tables.
  - `#work-tab-content`: Invoicing controls, search inputs, status/risk filters, and the invoices list.
- **Table Pagination**:
  - Always paginate the invoices table to show **10 invoices per page**.
  - Reset the active page to `1` when search queries, filters, or refresh hooks are triggered.
- **Rupee Currency Standard**:
  - The Indian Rupee symbol (`₹`) is the exclusive default currency. All frontend elements, detail inspector HTML templates, and printed PDF templates must display rates in `₹` using the helper `formatCurrency()`.
