# 🎓 Smart Fee Collection Engine
**Production-ready College Fee Management System**

---

## 📁 Project Structure
```
smart_fee_engine/
├── run.py                        ← One-click startup script
├── requirements.txt
├── README.md
├── backend/
│   └── app.py                    ← Flask REST API (all routes)
├── database/
│   ├── loader.py                 ← Excel → SQLite loader
│   ├── fee_engine.db             ← Auto-generated SQLite DB
│   └── smart_fee_collection_final.xlsx
├── frontend/
│   ├── index.html                ← Login Page (Student + Admin)
│   ├── shared/
│   │   ├── css/common.css
│   │   └── js/utils.js
│   ├── student/pages/
│   │   ├── dashboard.html        ← Fee summary + AI Chatbot
│   │   ├── profile.html          ← Student profile
│   │   ├── payments.html         ← Pay fees (Razorpay mock)
│   │   ├── history.html          ← Payment history
│   │   ├── emi.html              ← EMI plan request/view
│   │   └── receipts.html         ← Download receipts
│   └── admin/pages/
│       ├── dashboard.html        ← Admin analytics + charts
│       ├── students.html         ← View/search/edit students
│       ├── defaulters.html       ← Defaulter tracking
│       ├── emi-approvals.html    ← Approve/reject EMI
│       ├── reminders.html        ← Send reminders
│       ├── upload.html           ← Upload new dataset
│       └── analytics.html        ← Full Chart.js analytics
└── workflows/
    ├── n8n_reminder_workflow.json
    └── n8n_chatbot_workflow.json
```

---

## 🚀 Quick Start

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Start the backend
```bash
python run.py
```
This auto-creates the database from the Excel dataset.

### Step 3 — Open the frontend
Open `frontend/index.html` in your browser (or use Live Server in VS Code).

---

## 🔐 Login Credentials

| Role    | Username / ID | Password   |
|---------|--------------|------------|
| Admin   | `admin`      | `admin@123`|
| Student | `AIML001`    | `0001@Fee` |
| Student | `CSE005`     | `0005@Fee` |

**Student password formula:** Last 4 chars of Student ID + `@Fee`
- `AIML001` → `0001@Fee`
- `CSE012`  → `0012@Fee`

---

## 📡 REST API Endpoints

| Method | Endpoint                  | Description                        |
|--------|---------------------------|------------------------------------|
| POST   | `/login`                  | Student / Admin login              |
| GET    | `/student/dashboard`      | Student fee summary                |
| GET    | `/student/history`        | Payment transaction history        |
| GET    | `/student/emi`            | Student EMI plan details           |
| POST   | `/student/payment`        | Process fee payment                |
| POST   | `/student/emi/request`    | Request EMI plan                   |
| GET    | `/student/receipt/<id>`   | Download HTML receipt              |
| GET    | `/admin/students`         | List all students (search/filter)  |
| GET    | `/admin/analytics`        | Full analytics data                |
| GET    | `/admin/defaulters`       | Defaulter list                     |
| POST   | `/admin/fee/edit`         | Edit a student's fee record        |
| GET    | `/admin/emi/all`          | All EMI plan requests              |
| POST   | `/admin/emi/approve`      | Approve/reject EMI plan            |
| POST   | `/admin/reminders/send`   | Send due-date reminders            |
| POST   | `/admin/upload`           | Upload new Excel dataset           |
| POST   | `/chatbot`                | AI chatbot query                   |

---

## 🗄️ Database Schema

### `students`
| Column       | Type | Description              |
|--------------|------|--------------------------|
| student_id   | TEXT | Primary key (e.g. AIML001)|
| name         | TEXT | Full name                |
| department   | TEXT | AIML, CSE, Civil, etc.   |
| year         | INT  | Academic year            |
| email        | TEXT | Unique email             |
| parent_phone | TEXT | Parent contact           |
| password_hash| TEXT | SHA-256 hashed           |

### `fee_structure`
| Column           | Type | Description         |
|------------------|------|---------------------|
| student_id       | TEXT | FK → students       |
| total_fee        | REAL | Total fee amount    |
| paid_amount      | REAL | Amount paid         |
| pending_fee      | REAL | Balance due         |
| scholarship      | REAL | Scholarship amount  |
| due_date         | TEXT | Payment deadline    |
| fee_status       | TEXT | Fully Paid / Half Paid / Overdue |

### `payments`
| Column       | Type | Description         |
|--------------|------|---------------------|
| student_id   | TEXT | FK → students       |
| amount       | REAL | Amount paid         |
| method       | TEXT | UPI / Card / Net Banking |
| txn_id       | TEXT | Unique transaction ID|
| payment_date | TEXT | Date of payment     |
| receipt_no   | TEXT | Receipt reference   |

### `emi_plans`
| Column                  | Type | Description        |
|-------------------------|------|--------------------|
| student_id              | TEXT | FK → students      |
| installments            | INT  | Number of EMIs     |
| amount_per_installment  | REAL | Per EMI amount     |
| status                  | TEXT | Pending/Approved/Rejected |

---

## 🤖 n8n Automation Setup

1. Install n8n: `npx n8n`
2. Open: `http://localhost:5678`
3. Import `workflows/n8n_reminder_workflow.json`
4. Import `workflows/n8n_chatbot_workflow.json`
5. Configure email credentials in n8n
6. Activate both workflows

---

## 📊 Dataset (256 Students)

The included dataset covers:
- **6 Departments:** AIML, CSE, Civil, Mechanical, Electronics, Other
- **Fee Statuses:** Fully Paid (151), Half Paid (62), Overdue (43)
- **Fields:** Student ID, Name, Department, Year, Total Fee, Paid, Pending, Due Date, Scholarship, Email, Payment Method, Installment Plan, etc.

---

## 🛠️ Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | HTML5, CSS3, Vanilla JS           |
| Charts     | Chart.js v4                       |
| Backend    | Python Flask + Flask-CORS         |
| Database   | SQLite (via pandas + sqlite3)     |
| Dataset    | pandas + openpyxl (.xlsx loader)  |
| Automation | n8n (workflow JSON provided)      |
| Payment    | Razorpay/Stripe mock simulation   |

---

*Smart Fee Collection Engine — Final Year Project | Academic Year 2024-25*


python backend/app.py




cd Ai_Fee_engine-main\smart_fee_engine