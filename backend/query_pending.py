import sqlite3

def main():
    conn = sqlite3.connect('papermine.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, invoice_number, vendor_id, total_amount, due_date FROM invoices WHERE payment_status = 'Pending'")
    rows = cursor.fetchall()
    
    # Let's get column names
    col_names = [description[0] for description in cursor.description]
    
    # fetch all columns for a detailed view
    cursor.execute("SELECT * FROM invoices WHERE payment_status = 'Pending'")
    detailed_rows = cursor.fetchall()
    detailed_col_names = [description[0] for description in cursor.description]

    print("--- PENDING INVOICES SUMMARY ---")
    for row in rows:
        print(dict(zip(col_names, row)))
        
    print("\n--- FIRST 2 PENDING INVOICES DETAILED ---")
    for row in detailed_rows[:2]:
         print(dict(zip(detailed_col_names, row)))

    conn.close()

if __name__ == '__main__':
    main()
