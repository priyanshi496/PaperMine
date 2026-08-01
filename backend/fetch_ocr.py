import sqlite3

def fetch_latest_ocr():
    conn = sqlite3.connect("d:/PaperMine/backend/papermine.db")
    cursor = conn.cursor()
    # Fetch the latest document
    cursor.execute("SELECT id, filename, ocr_text FROM documents ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        doc_id, filename, ocr_text = row
        print(f"Document ID: {doc_id}")
        print(f"Filename: {filename}")
        print("--- OCR TEXT ---")
        print(ocr_text)
    else:
        print("No documents found.")
    conn.close()

if __name__ == "__main__":
    fetch_latest_ocr()
