import sqlite3
conn = sqlite3.connect('papermine.db')
cursor = conn.cursor()
cursor.execute("SELECT vendor_id, COUNT(*) FROM invoices WHERE payment_status = 'Pending' GROUP BY vendor_id")
print(cursor.fetchall())
conn.close()
