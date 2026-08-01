import random
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import Vendor, Invoice, LineItem, Document, DocumentChunk

db = SessionLocal()

vendors = db.query(Vendor).all()

if not vendors:
    print("No vendors found. Please run seed_db.py first.")
    exit()

print("Generating invoices for August 2026...")

def generate_faiss_chunk(vendor, inv_num, date, items, sub, tax, tot, risk_score):
    chunk = f"FULL INVOICE | Invoice No: {inv_num}\n"
    chunk += f"Vendor: {vendor.name}\n"
    chunk += f"GSTIN: {vendor.gstin}\n"
    chunk += f"Invoice Date: {date}\n"
    chunk += f"Department: {vendor.department}\n"
    chunk += f"Bank Details: {vendor.bank_account}, IFSC: {vendor.ifsc}\n"
    chunk += f"Risk Score: {risk_score}\n"
    chunk += "--- LINE ITEMS ---\n"
    for it in items:
        chunk += f"{it['desc']} | Qty: {it['qty']} | Rate: {it['rate']} | Amount: {it['amt']}\n"
    chunk += "--- TOTALS ---\n"
    chunk += f"Subtotal: {sub}\n"
    chunk += f"Total GST: {tax}\n"
    chunk += f"Grand Total: {tot}\n"
    return chunk

extra_vendors = [
    {
        "name": "OneBite Hapoli",
        "items": [("Hot Coffee", 90, "Beverage"), ("Cold Coffee", 150, "Beverage"), ("French Fries", 120, "Snack"), ("Chicken Burger", 200, "Snack"), ("Pizza", 350, "Food")]
    },
    {
        "name": "FreshFarm Dairy",
        "items": [("Milk 1L", 65, "Dairy"), ("Butter 500g", 250, "Dairy"), ("Cheese Slices", 150, "Dairy"), ("Paneer 1kg", 380, "Dairy"), ("Curd 1L", 80, "Dairy")]
    },
    {
        "name": "Dell Technologies India Pvt. Ltd.",
        "items": [("Dell XPS 13", 120000, "Hardware"), ("Laptop Bag", 2500, "Accessories"), ("Webcam", 4500, "Hardware")]
    },
    {
        "name": "METRO Wholesale India",
        "items": [("Water Bottles Pack", 200, "Grocery"), ("Tea Bags", 400, "Grocery"), ("Hand Wash", 150, "Supplies")]
    },
    {
        "name": "Office Depot India",
        "items": [("Printer Paper", 300, "Stationery"), ("Highlighters", 250, "Stationery"), ("Binder", 120, "Stationery")]
    }
]

def insert_invoice(data, vendor_obj):
    doc = Document(filename=f"{data['invoice_number']}.pdf", status="processed")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    pay_status = "Pending"
    ver_status = "Unverified"
    if data["status"] == "Paid":
        pay_status = "Paid"
        ver_status = "Paid"
    elif data["status"] == "Approved":
        ver_status = "Approved"
    elif data["status"] == "Vendor Confirmed":
        ver_status = "Vendor Confirmed"
    elif data["status"] == "Rejected":
        ver_status = "Rejected"

    inv = Invoice(
        document_id=doc.id, vendor_id=vendor_obj.id, invoice_number=data["invoice_number"],
        invoice_date=data["date"], due_date=data["due"], subtotal=data["subtotal"],
        tax_amount=data["tax"], total_amount=data["total"], department=vendor_obj.department,
        payment_status=pay_status, verification_status=ver_status, risk_score=data.get("risk", 0),
        uploaded_at=datetime.strptime(data["date"], "%Y-%m-%d") + timedelta(days=1)
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    for item in data["items"]:
        db.add(LineItem(invoice_id=inv.id, description=item["desc"], amount=str(item["amt"]), category=item["cat"]))
    
    vendor_obj.total_spent += float(data["total"])
    db.commit()

    chunk_text = generate_faiss_chunk(vendor_obj, data["invoice_number"], data["date"], data["items"], data["subtotal"], data["tax"], data["total"], data.get("risk", 0))
    chunk = DocumentChunk(document_id=doc.id, vendor_id=vendor_obj.id, document_type="invoice", chunk_text=chunk_text)
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk_text

documents_to_embed = []
start_date = datetime(2026, 8, 1)

for i in range(10):
    v_info = random.choice(extra_vendors)
    vendor_obj = next((v for v in vendors if v.name == v_info["name"]), None)
    if not vendor_obj:
        continue

    date = start_date + timedelta(days=random.randint(0, 25))
    date_str = date.strftime("%Y-%m-%d")
    due_str = (date + timedelta(days=15)).strftime("%Y-%m-%d")
    inv_num = f"{v_info['name'][:3].upper()}-AUG-{random.randint(1000, 9999)}"
    
    items = []
    sub = 0
    for _ in range(random.randint(2, 5)):
        desc, rate, cat = random.choice(v_info["items"])
        qty = random.randint(1, 10)
        amt = rate * qty
        sub += amt
        items.append({"desc": desc, "qty": qty, "rate": rate, "amt": amt, "cat": cat})
        
    tax = sub * 0.18
    tot = sub + tax
    
    status = random.choice(["Paid", "Approved", "Vendor Confirmed", "Vendor Confirmed", "Rejected"])
    risk = 0
    if status == "Vendor Confirmed": risk = random.randint(3, 7)
    if status == "Rejected": risk = random.randint(7, 10)
    
    data = {
        "vendor_name": v_info["name"], "invoice_number": inv_num,
        "date": date_str, "due": due_str, "subtotal": str(sub), "tax": str(tax), "total": str(tot),
        "items": items, "status": status, "risk": risk
    }
    
    chunk_text = insert_invoice(data, vendor_obj)
    documents_to_embed.append(chunk_text)

print(f"Generated {len(documents_to_embed)} invoices for August 2026.")

from app.services.vector_store import knowledge_engine
print(f"Rebuilding FAISS index with {len(documents_to_embed)} chunks...")
knowledge_engine.rebuild_index_from_db(db)
print("Done!")
