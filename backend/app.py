
from flask import Flask, jsonify, request, send_file, make_response
import sqlite3, hashlib, uuid, os
from datetime import datetime
from io import BytesIO
import sys
from .twilio_reminder import send_call_reminder
from flask import Response
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))


app = Flask(__name__)
app.secret_key = "sfce_secret_2025"

# TwiML endpoint for custom call message
@app.route('/twiml/fee_reminder.xml')
def twiml_fee_reminder():
    message = "Hello, this is a reminder from your college. Your fees payment is pending. Please complete the payment before the due date. Thank you."
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-US">{message}</Say>
</Response>'''
    return Response(twiml, mimetype='text/xml')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'fee_engine.db')


# SendGrid API Key (keep secure in production!)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "DUMMY_SENDGRID_KEY_FOR_PUSH")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "dummy@example.com")

def send_email_reminder(to_email, subject, content):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": SENDER_EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": content}]
    }
    r = requests.post(url, headers=headers, json=data)
    return r.status_code, r.text

# Admin endpoint to send reminder to a student (real email)
@app.route('/admin/send_reminder', methods=['POST'])
def admin_send_reminder():
    data = request.json
    student_id = data.get('student_id')
    subject = data.get('subject', 'Fee Payment Reminder')
    message = data.get('message', 'This is a reminder to pay your pending fees.')
    conn = db()
    row = conn.execute("SELECT email, name FROM students WHERE student_id=?", (student_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "error", "msg": "Student not found"}), 404
    email = row["email"]
    name = row["name"]
    status, resp = send_email_reminder(email, subject, f"Dear {name},\n\n{message}\n\n- Smart Fee Engine")
    if status == 202:
        return jsonify({"status": "sent", "to": email})
    else:
        return jsonify({"status": "error", "msg": resp}), 500
"""
Smart Fee Collection Engine — Flask Backend
Run: python app.py
"""
from flask import Flask, jsonify, request, send_file, make_response
import sqlite3, hashlib, uuid, os
from datetime import datetime
from io import BytesIO
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))

app = Flask(__name__)
app.secret_key = "sfce_secret_2025"

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'fee_engine.db')

# Warn if DB is missing
if not os.path.exists(DB_PATH):
    print("[ERROR] Database file not found at:", DB_PATH)
    print("Please run 'python run.py' from the smart_fee_engine folder to initialize the database.")
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

@app.after_request
def after_request(response):
    return cors(response)

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return cors(make_response()), 200

# ── AUTH ──────────────────────────────────────────────────────────────
@app.route('/login', methods=['POST','OPTIONS'])
def login():
    data = request.json
    role = data.get('role', 'student')
    uid  = data.get('id','').strip()
    pwd  = data.get('password','').strip()
    conn = db()
    if role == 'admin':
        row = conn.execute("SELECT * FROM admins WHERE username=? AND password_hash=?",
                           (uid, hash_pw(pwd))).fetchone()
        conn.close()
        if row: return jsonify({"status":"ok","role":"admin","username":uid})
        return jsonify({"status":"error","msg":"Invalid credentials"}), 401
    row = conn.execute(
        "SELECT s.*, f.* FROM students s JOIN fee_structure f ON s.student_id=f.student_id "
        "WHERE (s.student_id=? OR s.email=?) AND s.password_hash=?",
        (uid, uid.lower(), hash_pw(pwd))).fetchone()
    conn.close()
    if row: return jsonify({"status":"ok","role":"student","student_id":row["student_id"],"name":row["name"]})
    return jsonify({"status":"error","msg":"Invalid credentials"}), 401

# ── STUDENT ───────────────────────────────────────────────────────────
@app.route('/student/dashboard')
def student_dashboard():
    sid = request.args.get('student_id')
    conn = db()
    s = conn.execute(
        "SELECT s.student_id, s.name, s.department, s.year, s.email, s.parent_phone, "
        "f.total_fee, f.paid_amount, f.pending_fee, f.scholarship, "
        "f.due_date, f.fee_status, f.defaulter_status "
        "FROM students s JOIN fee_structure f ON s.student_id=f.student_id WHERE s.student_id=?", (sid,)).fetchone()
    conn.close()
    if not s: return jsonify({"error":"Not found"}), 404
    return jsonify(dict(s))

@app.route('/student/history')
def student_history():
    sid = request.args.get('student_id')
    conn = db()
    rows = conn.execute("SELECT * FROM payments WHERE student_id=? ORDER BY payment_date DESC", (sid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/student/emi')
def student_emi():
    sid = request.args.get('student_id')
    conn = db()
    row = conn.execute("SELECT * FROM emi_plans WHERE student_id=?", (sid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})

@app.route('/student/payment', methods=['POST','OPTIONS'])
def student_payment():
    data = request.json
    sid = data.get('student_id')
    amount = float(data.get('amount', 0))
    method = data.get('method', 'Online')
    conn = db()
    fs = conn.execute("SELECT * FROM fee_structure WHERE student_id=?", (sid,)).fetchone()
    if not fs: conn.close(); return jsonify({"error":"Not found"}), 404
    new_paid = float(fs['paid_amount']) + amount
    new_pending = max(0, float(fs['total_fee']) - new_paid)
    status = "Fully Paid" if new_pending == 0 else "Half Paid"
    txn_id = "TXN" + uuid.uuid4().hex[:10].upper()
    receipt = "RCP" + sid + datetime.now().strftime("%m%d%H%M")
    conn.execute("UPDATE fee_structure SET paid_amount=?, pending_fee=?, fee_status=?, defaulter_status=? WHERE student_id=?",
                 (new_paid, new_pending, status, "Paid" if new_pending == 0 else "Pending", sid))
    conn.execute("INSERT INTO payments (student_id,amount,method,txn_id,payment_date,status,receipt_no) VALUES (?,?,?,?,?,?,?)",
                 (sid, amount, method, txn_id, datetime.now().strftime("%Y-%m-%d"), "Success", receipt))
    conn.commit(); conn.close()
    return jsonify({"status":"success","txn_id":txn_id,"receipt_no":receipt,"paid":new_paid,"pending":new_pending,"fee_status":status})

@app.route('/student/emi/request', methods=['POST','OPTIONS'])
def request_emi():
    data = request.json
    sid = data.get('student_id')
    installments = int(data.get('installments', 3))
    conn = db()
    fs = conn.execute("SELECT * FROM fee_structure WHERE student_id=?", (sid,)).fetchone()
    if not fs: conn.close(); return jsonify({"error":"Not found"}), 404
    per_inst = round(float(fs['pending_fee']) / installments, 2)
    conn.execute("INSERT OR REPLACE INTO emi_plans (student_id,total_amount,installments,amount_per_installment,status) VALUES (?,?,?,?,?)",
                 (sid, float(fs['pending_fee']), installments, per_inst, "Pending"))
    conn.commit(); conn.close()
    return jsonify({"status":"requested","installments":installments,"per_installment":per_inst})


# Improved receipt download with error handling
@app.route('/student/receipt/<receipt_no>')
def download_receipt(receipt_no):
        try:
                conn = db()
                p = conn.execute("SELECT p.*, s.name, s.department FROM payments p JOIN students s ON p.student_id=s.student_id WHERE p.receipt_no=?", (receipt_no,)).fetchone()
                conn.close()
                if not p:
                        return '<h2 style="color:#ef4444;text-align:center;margin-top:60px">Receipt not found.</h2>', 404
                p = dict(p)
                html = f"""<!DOCTYPE html><html><head><title>Fee Receipt</title>
                <style>body{{font-family:Arial,sans-serif;padding:40px;max-width:700px;margin:0 auto;}}
                .header{{background:#1e3a5f;color:#fff;padding:24px;text-align:center;border-radius:10px 10px 0 0;}}
                .header h2{{margin:0;font-size:22px;}}.header p{{margin:4px 0 0;opacity:0.8;font-size:13px;}}
                table{{width:100%;border-collapse:collapse;margin-top:20px;border:1px solid #e2e8f0;}}
                td{{padding:12px 16px;border:1px solid #e2e8f0;font-size:14px;}}
                .label{{background:#f8fafc;font-weight:600;width:40%;color:#374151;}}
                .footer{{text-align:center;margin-top:30px;color:#9ca3af;font-size:12px;border-top:1px solid #e2e8f0;padding-top:16px;}}
                .stamp{{display:inline-block;border:3px solid #10b981;color:#10b981;padding:6px 20px;border-radius:4px;font-size:18px;font-weight:800;transform:rotate(-5deg);margin:10px;}}
                </style></head><body>
                <div class="header"><h2>🎓 Smart Fee Collection Engine</h2><p>Official Fee Payment Receipt</p></div>
                <table>
                    <tr><td class="label">Receipt No.</td><td><strong>{p['receipt_no']}</strong></td><td class="label">Payment Date</td><td>{p['payment_date']}</td></tr>
                    <tr><td class="label">Student ID</td><td>{p['student_id']}</td><td class="label">Student Name</td><td>{p['name']}</td></tr>
                    <tr><td class="label">Department</td><td>{p['department']}</td><td class="label">Transaction ID</td><td><code>{p['txn_id']}</code></td></tr>
                    <tr><td class="label">Amount Paid</td><td><strong style="font-size:18px;color:#1e3a5f;">₹{float(p['amount']):,.2f}</strong></td><td class="label">Payment Method</td><td>{p['method']}</td></tr>
                    <tr><td class="label">Payment Status</td><td colspan="3"><span style="color:#10b981;font-weight:700;font-size:16px;">✅ {p['status']}</span></td></tr>
                </table>
                <div style="text-align:center;margin-top:20px;"><span class="stamp">PAID</span></div>
                <div class="footer"><p>This is a computer-generated receipt. No physical signature is required.</p><p>Smart Fee Collection Engine | Academic Year 2024-25</p></div>
                </body></html>"""
                buf = BytesIO(html.encode())
                return send_file(buf, mimetype='text/html', as_attachment=False, download_name='fee_receipt.html')
        except Exception as e:
                return f'<h2 style="color:#ef4444;text-align:center;margin-top:60px">Error generating receipt: {str(e)}</h2>', 500

# ── ADMIN ─────────────────────────────────────────────────────────────
@app.route('/admin/send_call_reminder', methods=['POST'])
def admin_send_call_reminder():
    data = request.json
    to_phone = data.get('to_phone')
    if not to_phone:
        return jsonify({"status": "error", "msg": "Missing 'to_phone' parameter"}), 400
    try:
        # Use NGROK_BASE_URL if set, else fallback to request.host_url
        # Use Twilio's default demo voice message
        demo_url = "http://demo.twilio.com/docs/voice.xml"
        sid = send_call_reminder(to_phone, url=demo_url)
        return jsonify({"status": "sent", "sid": sid})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500
@app.route('/admin/students')
def admin_students():
    search = request.args.get('search','')
    dept   = request.args.get('dept','')
    conn = db()
    query = ("SELECT s.student_id, s.name, s.department, s.year, s.email, "
             "f.total_fee, f.paid_amount, f.pending_fee, f.due_date, f.fee_status, f.defaulter_status "
             "FROM students s JOIN fee_structure f ON s.student_id=f.student_id WHERE 1=1")
    params = []
    if search:
        query += " AND (s.name LIKE ? OR s.student_id LIKE ? OR s.email LIKE ?)"
        params += [f"%{search}%"]*3
    if dept:
        query += " AND s.department=?"; params.append(dept)
    rows = conn.execute(query + " ORDER BY s.student_id", params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/admin/analytics')
def admin_analytics():
    conn = db()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_fee      = conn.execute("SELECT SUM(total_fee) FROM fee_structure").fetchone()[0] or 0
    total_collected= conn.execute("SELECT SUM(paid_amount) FROM fee_structure").fetchone()[0] or 0
    total_pending  = conn.execute("SELECT SUM(pending_fee) FROM fee_structure").fetchone()[0] or 0
    defaulters     = conn.execute("SELECT COUNT(*) FROM fee_structure WHERE defaulter_status IN ('Overdue','Pending')").fetchone()[0]
    dept_data      = conn.execute("SELECT s.department, SUM(f.total_fee) as total, SUM(f.paid_amount) as paid, SUM(f.pending_fee) as pending FROM students s JOIN fee_structure f ON s.student_id=f.student_id GROUP BY s.department").fetchall()
    monthly        = conn.execute("SELECT strftime('%Y-%m', payment_date) as month, SUM(amount) as collected FROM payments GROUP BY month ORDER BY month DESC LIMIT 12").fetchall()
    status_dist    = conn.execute("SELECT fee_status, COUNT(*) as cnt FROM fee_structure GROUP BY fee_status").fetchall()
    conn.close()
    return jsonify({"summary":{"total_students":total_students,"total_fee":round(total_fee,2),"total_collected":round(total_collected,2),"total_pending":round(total_pending,2),"defaulters":defaulters},
                    "by_department":[dict(r) for r in dept_data],
                    "monthly_collection":[dict(r) for r in monthly],
                    "status_distribution":[dict(r) for r in status_dist]})

@app.route('/admin/defaulters')
def admin_defaulters():
    conn = db()
    rows = conn.execute("SELECT s.student_id, s.name, s.department, s.year, s.email, f.pending_fee, f.due_date, f.defaulter_status FROM students s JOIN fee_structure f ON s.student_id=f.student_id WHERE f.defaulter_status IN ('Overdue','Pending') AND f.pending_fee > 0 ORDER BY f.pending_fee DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/admin/fee/edit', methods=['POST','OPTIONS'])
def admin_edit_fee():
    data = request.json
    sid = data.get('student_id')
    conn = db()
    fields = {k: data[k] for k in ['total_fee','paid_amount','pending_fee','due_date','fee_status'] if k in data}
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE fee_structure SET {sets} WHERE student_id=?", list(fields.values()) + [sid])
        conn.commit()
    conn.close()
    return jsonify({"status":"updated"})

@app.route('/admin/emi/all')
def all_emi():
    conn = db()
    rows = conn.execute("SELECT e.*, s.name, s.department FROM emi_plans e JOIN students s ON e.student_id=s.student_id ORDER BY e.requested_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/admin/emi/approve', methods=['POST','OPTIONS'])
def approve_emi():
    data = request.json
    conn = db()
    conn.execute("UPDATE emi_plans SET status=?, approved_at=? WHERE id=?",
                 (data.get('action','Approved'), datetime.now().strftime("%Y-%m-%d"), data.get('emi_id')))
    conn.commit(); conn.close()
    return jsonify({"status":data.get('action')})

@app.route('/admin/reminders/send', methods=['POST','OPTIONS'])
def send_reminders():
    conn = db()
    overdue = conn.execute("SELECT s.student_id, s.name, s.email, f.pending_fee, f.due_date FROM students s JOIN fee_structure f ON s.student_id=f.student_id WHERE f.pending_fee > 0 AND f.due_date <= date('now', '+30 days')").fetchall()
    count = 0
    for r in overdue:
        msg = f"Dear {r['name']}, your pending fee of ₹{r['pending_fee']:,.0f} is due on {r['due_date']}."
        conn.execute("INSERT INTO reminders (student_id, reminder_type, message) VALUES (?,?,?)", (r['student_id'], "Due Date Alert", msg))
        count += 1
    conn.commit(); conn.close()
    return jsonify({"status":"sent","count":count})

@app.route('/admin/upload', methods=['POST','OPTIONS'])
def upload_dataset():
    if 'file' not in request.files: return jsonify({"error":"No file"}), 400
    f = request.files['file']
    save_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'smart_fee_collection_final.xlsx')
    f.save(save_path)
    try:
        from loader import load_excel_to_db
        load_excel_to_db()
        return jsonify({"status":"uploaded and reloaded"})
    except Exception as e:
        return jsonify({"status":"uploaded","note":str(e)})

# ── CHATBOT ───────────────────────────────────────────────────────────
@app.route('/chatbot', methods=['POST','OPTIONS'])
def chatbot():
    data = request.json
    sid = data.get('student_id','')
    msg = data.get('message','').lower()
    conn = db()
    if not sid: conn.close(); return jsonify({"reply":"Please provide your Student ID."})
    s = conn.execute("SELECT s.name, f.total_fee, f.paid_amount, f.pending_fee, f.due_date, f.fee_status FROM students s JOIN fee_structure f ON s.student_id=f.student_id WHERE s.student_id=?", (sid,)).fetchone()
    if not s: conn.close(); return jsonify({"reply":"Student ID not found."})
    last_pay = conn.execute("SELECT payment_date, amount FROM payments WHERE student_id=? ORDER BY payment_date DESC LIMIT 1", (sid,)).fetchone()
    conn.close()
    if any(w in msg for w in ["pending","due","balance","remaining","unpaid"]):
        return jsonify({"reply":f"Hi {s['name']}! Your pending fee is ₹{s['pending_fee']:,.0f}. Due date: {s['due_date']}."})
    elif any(w in msg for w in ["last payment","paid","payment date"]):
        if last_pay: return jsonify({"reply":f"Your last payment of ₹{last_pay['amount']:,.0f} was on {last_pay['payment_date']}."})
        return jsonify({"reply":"No payment records found yet."})
    elif any(w in msg for w in ["total fee","fees","total"]):
        return jsonify({"reply":f"Total: ₹{s['total_fee']:,.0f} | Paid: ₹{s['paid_amount']:,.0f} | Status: {s['fee_status']}."})
    elif any(w in msg for w in ["due date","deadline","when"]):
        return jsonify({"reply":f"Your fee due date is {s['due_date']}."})
    elif any(w in msg for w in ["hi","hello","hey"]):
        return jsonify({"reply":f"Hello {s['name']}! 👋 How can I help with your fee queries today?"})
    elif any(w in msg for w in ["emi","installment","plan"]):
        return jsonify({"reply":"Apply for an EMI plan from your dashboard under the 'EMI Plan' section."})
    else:
        return jsonify({"reply":"I can help with: pending fees, payment history, total fees, due dates, or EMI plans!"})

if __name__ == '__main__':
    print("🎓 Smart Fee Collection Engine running on http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')
