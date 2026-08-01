import sqlite3
import pandas as pd

conn = sqlite3.connect('papermine.db')
print("--- Invoices ---")
print(pd.read_sql_query("SELECT id, invoice_number, document_id, vendor_id FROM invoices WHERE invoice_number = 'OBH-2026-9999'", conn))

print("\n--- Document Chunks ---")
print(pd.read_sql_query("SELECT dc.id, dc.document_id, d.filename, substring(dc.chunk_text, 1, 50) as text_preview FROM document_chunks dc JOIN documents d ON dc.document_id = d.id WHERE dc.document_id IN (SELECT document_id FROM invoices WHERE invoice_number = 'OBH-2026-9999')", conn))

conn.close()
