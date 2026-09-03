"""
Smart Fee Collection Engine — Dataset Loader
Reads the Excel dataset, cleans it, and seeds the SQLite database.
"""
import sqlite3, pandas as pd, os, hashlib, uuid
import re
from datetime import datetime

DB_PATH   = os.path.join(os.path.dirname(__file__), "fee_engine.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "smart_fee_collection_final.xlsx")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        department TEXT, year INTEGER, email TEXT UNIQUE,
        parent_phone TEXT, password_hash TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS fee_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT UNIQUE,
        total_fee REAL DEFAULT 0, paid_amount REAL DEFAULT 0,
        pending_fee REAL DEFAULT 0, scholarship REAL DEFAULT 0,
        due_date TEXT, fee_status TEXT DEFAULT 'Pending',
        defaulter_status TEXT DEFAULT 'Pending',
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
        amount REAL, method TEXT, txn_id TEXT UNIQUE,
        payment_date TEXT, status TEXT DEFAULT 'Success', receipt_no TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    CREATE TABLE IF NOT EXISTS emi_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
        total_amount REAL, installments INTEGER,
        amount_per_installment REAL, paid_installments INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Pending', requested_at TEXT DEFAULT (datetime('now')),
        approved_at TEXT, FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
        reminder_type TEXT, message TEXT,
        sent_at TEXT DEFAULT (datetime('now')), status TEXT DEFAULT 'Sent',
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
        password_hash TEXT, email TEXT, created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit(); conn.close()
    print("[DB] Tables created.")

def hash_password(plain):
    return hashlib.sha256(plain.encode()).hexdigest()

def load_excel_to_db():
    # Load the first sheet regardless of its name
    df = pd.read_excel(EXCEL_PATH, sheet_name=0)
    df.columns = [c.strip().upper().replace(" ","_") for c in df.columns]
    df = df.dropna(subset=["STUDENT_ID","EMAIL"])
    df["DUE_DATE"] = pd.to_datetime(df["DUE_DATE"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["LAST_PAYMENT_DATE"] = pd.to_datetime(df["LAST_PAYMENT_DATE"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.fillna({"PAID_AMOUNT":0,"PENDING_FEE":0,"SCHOLARSHIP_AMOUNT":0,
                    "INSTALLMENT_COUNT":1,"INSTALLMENT_AMOUNT":0})
    conn = get_conn(); c = conn.cursor()
    # Clear old data before loading new dataset
    c.execute("DELETE FROM payments")
    c.execute("DELETE FROM fee_structure")
    c.execute("DELETE FROM students")
    c.execute("DELETE FROM emi_plans")
    c.execute("DELETE FROM reminders")
    for _, row in df.iterrows():
        sid = str(row["STUDENT_ID"]).strip()
        email = str(row["EMAIL"]).strip().lower()
        # Force update for Resham Mishra AIML024
        if sid == "AIML024":
            email = "resham.mishraaiml2023@indoreinstitute.com"
        numeric_suffix = re.search(r"(\d+)$", sid)
        password_suffix = numeric_suffix.group(1).zfill(4) if numeric_suffix else sid[-4:]
        pwd = hash_password(password_suffix + "@Fee")
        c.execute("INSERT OR REPLACE INTO students (student_id,name,department,year,email,parent_phone,password_hash) VALUES (?,?,?,?,?,?,?)",
            (sid, row["STUDENT_NAME"], row["DEPARTMENT"], int(row["YEAR"]), email, str(row["PARENT_PHONE"]), pwd))
        c.execute("INSERT OR REPLACE INTO fee_structure (student_id,total_fee,paid_amount,pending_fee,scholarship,due_date,fee_status,defaulter_status) VALUES (?,?,?,?,?,?,?,?)",
            (sid, float(row["TOTAL_FEE"]), float(row["PAID_AMOUNT"]), float(row["PENDING_FEE"]),
             float(row["SCHOLARSHIP_AMOUNT"]), row["DUE_DATE"], row["FEE_STATUS"], row["DEFAULTER_STATUS"]))
        if str(row.get("INSTALLMENT_PLAN","No")) == "Yes":
            c.execute("INSERT OR IGNORE INTO emi_plans (student_id,total_amount,installments,amount_per_installment,status) VALUES (?,?,?,?,?)",
                (sid, float(row["TOTAL_FEE"]), int(row["INSTALLMENT_COUNT"]), float(row["INSTALLMENT_AMOUNT"]), "Approved"))
        lp = row.get("LAST_PAYMENT_DATE","")
        if pd.notna(lp) and str(lp) != "NaT" and float(row["PAID_AMOUNT"]) > 0:
            txn = "TXN" + uuid.uuid4().hex[:10].upper()
            rcp = "RCP" + sid
            c.execute("INSERT OR IGNORE INTO payments (student_id,amount,method,txn_id,payment_date,status,receipt_no) VALUES (?,?,?,?,?,?,?)",
                (sid, float(row["PAID_AMOUNT"]), row.get("PAYMENT_METHOD","Online"), txn, str(lp), "Success", rcp))
    c.execute("INSERT OR IGNORE INTO admins (username,password_hash,email) VALUES (?,?,?)",
        ("admin", hash_password("admin@123"), "admin@college.edu"))
    conn.commit(); conn.close()
    print(f"[DB] Loaded {len(df)} students.")

if __name__ == "__main__":
    init_db()
    load_excel_to_db()
    print("[DB] Ready:", DB_PATH)
