"""
Smart Fee Collection Engine — Startup Script
Usage: python run.py
"""
import os, sys

DB_PATH = os.path.join('database', 'fee_engine.db')
if not os.path.exists(DB_PATH):
    print("🔧 Initializing database...")
    sys.path.insert(0, 'database')
    from loader import init_db, load_excel_to_db
    init_db()
    load_excel_to_db()
    print("✅ Database ready!\n")

print("🚀 Starting Smart Fee Collection Engine...")
print("📌 Backend API: http://localhost:5001")
print("🌐 Open frontend: frontend/index.html")
print("─" * 45)

os.chdir('backend')
os.system(f'"{sys.executable}" app.py')
