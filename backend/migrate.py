import sqlite3

conn = sqlite3.connect("papermine.db")
cursor = conn.cursor()

# Vendors
try:
    cursor.execute("ALTER TABLE vendors ADD COLUMN late_invoices INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE vendors ADD COLUMN duplicate_invoices INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE vendors ADD COLUMN compliance_issues INTEGER DEFAULT 0;")
    print("Vendor columns added")
except Exception as e:
    print("Vendor columns may already exist:", e)

# Invoices
try:
    cursor.execute("ALTER TABLE invoices ADD COLUMN risk_score INTEGER DEFAULT 0;")
    print("Invoice columns added")
except Exception as e:
    print("Invoice columns may already exist:", e)

# InsightAlerts
try:
    cursor.execute("ALTER TABLE insight_alerts ADD COLUMN explanation TEXT;")
    cursor.execute("ALTER TABLE insight_alerts ADD COLUMN confidence_score INTEGER;")
    print("InsightAlert columns added")
except Exception as e:
    print("InsightAlert columns may already exist:", e)

conn.commit()
conn.close()
print("Migration completed.")
