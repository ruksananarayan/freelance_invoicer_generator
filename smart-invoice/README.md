# Smart Freelance Invoice & Payment Risk System (CTS Invoice Guard)

> An intelligent web application extending basic freelance invoice generation into a proactive **Payment Risk Scoring & Prioritization Platform** built with Flask, SQLite, Docker, and Google Cloud Run deployment.

---

## 📁 Repository Directory Structure

```
smart-invoice/
│
├── app.py                     # Main Flask application & REST APIs
├── requirements.txt           # Python package dependencies
├── Dockerfile                 # Multi-stage container build (Exposes $PORT for Cloud Run)
├── gcs_helper.py              # GCP Cloud Storage PDF bucket helper
├── deploy_cloud_run.sh        # Automated GCP Cloud Run deployment script
├── README.md                  # Project documentation & GCP architecture
├── .gitignore
│
├── database/
│   ├── __init__.py
│   ├── database.py            # SQLite helper functions (CRUD & user scoping)
│   └── invoice.db             # Local SQLite database file
│
├── templates/
│   ├── index.html             # Single-Page Interactive Dashboard & Workspace
│   ├── history.html           # Dedicated Invoice History Matrix view
│   └── invoice.html           # Standalone single invoice printable view
│
├── static/
│   ├── css/
│   │   └── styles.css         # Dark glassmorphic styling & high-contrast PDF layout
│   └── js/
│       └── app.js             # Interactive JavaScript (Auth, Live Math, PDF generator)
│
├── risk_engine/
│   ├── __init__.py
│   └── risk.py                # Overdue Risk Scoring Engine (0-100 explainable score algorithm)
│
└── tests/
    └── test_risk.py           # Python unit tests
```

---

## 🌟 Team GitHub Workflow

For a team of 8 working on one repository:

1. **Main Branch Protection**:
   - `main`: Production-ready code deployed to Cloud Run.
2. **Feature Branching**:
   - Each developer creates a topic branch:
     - `git checkout -b feature/auth-view`
     - `git checkout -b feature/gcs-pdf-upload`
     - `git checkout -b feature/risk-engine-tuning`
3. **Pull Request (PR) & Merging**:
   - Push feature branch to GitHub: `git push origin feature/auth-view`
   - Open a Pull Request into `main` with team review & approval before merging.

---

## 🚀 Running Locally

```bash
# 1. Navigate to the project directory
cd smart-invoice

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run application
python app.py
```
Open your browser at `http://localhost:8080` (or port 5000).

---

## 🐳 Docker Containerization

Test containerizing your application locally before deploying to GCP:

```bash
# 1. Build the Docker image
docker build -t smart-invoice .

# 2. Run container locally on port 8080
docker run -p 8080:8080 -e PORT=8080 smart-invoice
```

---

## ☁️ GCP Cloud Run Deployment

### Option A: Direct Source Deployment (Recommended)
Deploy directly from your project directory using Google Cloud buildpacks/Cloud Build:

```bash
# Deploy to Cloud Run with public access
gcloud run deploy smart-invoice \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

### Option B: Using script
```bash
chmod +x deploy_cloud_run.sh
./deploy_cloud_run.sh
```

---

## 🏛️ GCP Cloud Architecture & Scaling

```
                 INTERNET / USER
                        │
                        ▼
            ┌───────────────────────┐
            │    Google Cloud Run   │
            │   Container (Flask)   │
            └───────────┬───────────┘
                        │
      ┌─────────────────┼─────────────────┐
      │                 │                 │
      ▼                 ▼                 ▼
[ Database ]      [ Risk Engine ]     [ PDF Engine ]
(SQLite / Cloud   (Explainable 0-100   (Html2Pdf / GCS
     SQL)          Risk Score)          Bucket)
      │                 │                 │
      └─────────────────┼─────────────────┘
                        │
                        ▼
              [ GCP Cloud Logging ]
```

### Hackathon Architecture (SQLite local/POC)
- **Database**: Embedded SQLite file stored at `database/invoice.db`.
- **PDF Generation**: Client-side `html2pdf.js` & `@media print` formatting.

### Production Enterprise Architecture (For Judge Q&A)
1. **Database**: Replace SQLite with **Google Cloud SQL (PostgreSQL)** or **Firestore** for multi-AZ high availability and zero file-locking concurrency issues.
2. **PDF Storage**: Store generated PDF files in a **Google Cloud Storage Bucket** (`smart-invoice-pdfs`) via `gcs_helper.py`.
3. **Observability**: **Google Cloud Logging** captures request metrics, risk scoring events, and error tracebacks automatically.

---

## ☁️ 2. Corresponding Free-Tier Google Services

The table below outlines the 10 Google Cloud Services utilized across the platform architecture and how each operates within GCP's **Always Free Tier** allowance:

| GCP Service | Purpose | Always Free Allowance |
| :--- | :--- | :--- |
| **Cloud Run** | Host invoice application | 2 Million requests/mo, 360k GB-sec memory |
| **Firestore** | Store invoices | 1 GB storage, 50k reads/day, 20k writes/day |
| **Cloud Storage** | Store generated invoice documents | 5 GB-months standard storage in `us-central1` |
| **Cloud Run Functions** | Invoice processing | 2 Million invocations/mo |
| **Natural Language API** | Extract structured invoice information | 5,000 units/mo free tier |
| **Cloud Logging** | Logs | 50 GB log ingestion/mo free |
| **Cloud Monitoring** | Monitoring | All basic metrics & dashboards included |
| **Cloud Build** | Deployment | 120 build-minutes per day |
| **Artifact Registry** | Containers | 0.5 GB (500 MB) storage per month |
| **Secret Manager** | Secure credentials | 6 active secret versions per month |


---

## 🧪 Verification & Unit Tests

Run automated unit tests:
```bash
python -m unittest tests/test_risk.py
```
