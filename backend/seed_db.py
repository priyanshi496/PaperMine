"""
Database Seeding Script for PaperMine AP Platform.
Populates vendors, users, invoices, line items, alerts, and FAISS chunks.
"""
import os
import random
from datetime import datetime, timedelta

from app.db.database import SessionLocal, engine, Base
from app.db.models import User, Vendor, Invoice, LineItem, Document, DocumentChunk, InsightAlert
from app.services.vector_store import knowledge_engine
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

db = SessionLocal()

print("Clearing existing data...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# 1. Create Vendors
print("Creating vendors...")
vendors_data = [
    {"name": "OneBite Hapoli", "gstin": "24ABCDE1234F1Z5", "department": "Cafeteria", "bank": "HDFC0001234", "ifsc": "HDFC0001234"},
    {"name": "METRO Wholesale India", "gstin": "27AAACM1234N1Z5", "department": "Admin", "bank": "SBI0009876", "ifsc": "SBIN0009876"},
    {"name": "Dell Technologies India Pvt. Ltd.", "gstin": "29AADCD1234A1Z5", "department": "IT", "bank": "ICICI0005678", "ifsc": "ICIC0005678"},
    {"name": "Office Depot India", "gstin": "27AAAAO1234O1Z5", "department": "Admin", "bank": "AXIS0004321", "ifsc": "UTIB0004321"},
    {"name": "FreshFarm Dairy", "gstin": "24AAACF1234F1Z5", "department": "Cafeteria", "bank": "BOB0001111", "ifsc": "BARB0HAPOLI"}
]

db_vendors = {}
for i, v in enumerate(vendors_data):
    vendor = Vendor(
        name=v["name"],
        gstin=v["gstin"],
        department=v["department"],
        bank_account=v["bank"],
        ifsc=v["ifsc"],
        is_verified=1,
        trust_score=random.randint(85, 100),
        address=f"{v['name']} Main Office, India"
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    db_vendors[v["name"]] = vendor

# 2. Create Users
print("Creating users...")
users_to_create = [
    {"email": "cfo@technova.com", "role": "cfo", "vendor_id": None},
    {"email": "finance@technova.com", "role": "finance_team", "vendor_id": None},
]
for v_name, vendor in db_vendors.items():
    safe_name = v_name.split()[0].lower()
    users_to_create.append({
        "email": f"{safe_name}@vendor.com",
        "role": "vendor",
        "vendor_id": vendor.id
    })

for u in users_to_create:
    user = User(
        email=u["email"],
        hashed_password=get_password_hash("password123"),
        role=u["role"],
        vendor_id=u["vendor_id"]
    )
    db.add(user)
db.commit()

# 3. Specific 9 Invoices provided by user
print("Creating specific sample invoices...")
specific_invoices = [
    {
        "vendor_name": "Dell Technologies India Pvt. Ltd.", "invoice_number": "DLT-2026-0001",
        "date": "2026-05-15", "due": "2026-05-29", "subtotal": "277950", "tax": "50031", "total": "327981",
        "items": [
            {"desc": "Dell Latitude 5450 Laptop", "qty": 3, "rate": 78900, "amt": 236700, "cat": "Hardware"},
            {"desc": "Dell Wireless Mouse MS3320W", "qty": 5, "rate": 1650, "amt": 8250, "cat": "Hardware"},
            {"desc": "Dell USB-C Dock WD19S 130W", "qty": 2, "rate": 16500, "amt": 33000, "cat": "Hardware"}
        ],
        "status": "Approved", "risk": 0
    },
    {
        "vendor_name": "Dell Technologies India Pvt. Ltd.", "invoice_number": "DLT-2026-0002",
        "date": "2026-05-15", "due": "2026-05-29", "subtotal": "109600", "tax": "19728", "total": "129328",
        "items": [
            {"desc": "Dell 27-inch Monitor S2722QC", "qty": 4, "rate": 24400, "amt": 97600, "cat": "Hardware"},
            {"desc": "Dell Wired Keyboard KB216", "qty": 10, "rate": 750, "amt": 7500, "cat": "Hardware"},
            {"desc": "HDMI Cable 2 Meter", "qty": 10, "rate": 450, "amt": 4500, "cat": "Hardware"}
        ],
        "status": "Paid", "risk": 0
    },
    {
        "vendor_name": "Dell Technologies India Pvt. Ltd.", "invoice_number": "DLT-2026-0003",
        "date": "2026-05-15", "due": "2026-05-29", "subtotal": "335000", "tax": "60300", "total": "395300",
        "items": [
            {"desc": "Dell Precision 3660 Tower", "qty": 2, "rate": 145500, "amt": 291000, "cat": "Hardware"},
            {"desc": "APC Back-UPS Pro BX1100LI-IN", "qty": 2, "rate": 9500, "amt": 19000, "cat": "Hardware"},
            {"desc": "Samsung T7 Shield 1TB SSD", "qty": 2, "rate": 12500, "amt": 25000, "cat": "Hardware"}
        ],
        "status": "Vendor Confirmed", "risk": 0
    },
    {
        "vendor_name": "METRO Wholesale India", "invoice_number": "MTR-2026-2001",
        "date": "2026-05-10", "due": "2026-05-24", "subtotal": "32200", "tax": "1610", "total": "33810",
        "items": [
            {"desc": "Basmati Rice 25kg", "qty": 10, "rate": 2050, "amt": 20500, "cat": "Grocery"},
            {"desc": "Cooking Oil 15L", "qty": 6, "rate": 1750, "amt": 10500, "cat": "Grocery"},
            {"desc": "Sugar", "qty": 20, "rate": 52, "amt": 1040, "cat": "Grocery"},
            {"desc": "Salt", "qty": 10, "rate": 16, "amt": 160, "cat": "Grocery"}
        ],
        "status": "Approved", "risk": 0
    },
    {
        "vendor_name": "METRO Wholesale India", "invoice_number": "MTR-2026-2002",
        "date": "2026-05-12", "due": "2026-05-26", "subtotal": "21500", "tax": "2542", "total": "24042",
        "items": [
            {"desc": "Tea Powder 1kg", "qty": 15, "rate": 310, "amt": 4650, "cat": "Grocery"},
            {"desc": "Coffee Powder 500g", "qty": 20, "rate": 245, "amt": 4900, "cat": "Grocery"},
            {"desc": "Flour (Atta) 10kg", "qty": 25, "rate": 420, "amt": 10500, "cat": "Grocery"},
            {"desc": "Toor Dal 1kg", "qty": 10, "rate": 145, "amt": 1450, "cat": "Grocery"}
        ],
        "status": "Paid", "risk": 0
    },
    {
        "vendor_name": "METRO Wholesale India", "invoice_number": "MTR-2026-2003",
        "date": "2026-05-14", "due": "2026-05-28", "subtotal": "5450", "tax": "981", "total": "6431",
        "items": [
            {"desc": "Paper Cups 150ml", "qty": 30, "rate": 45, "amt": 1350, "cat": "Supplies"},
            {"desc": "Cleaning Liquid 1L", "qty": 20, "rate": 95, "amt": 1900, "cat": "Supplies"},
            {"desc": "Tissue Boxes (100 Pulls)", "qty": 40, "rate": 55, "amt": 2200, "cat": "Supplies"}
        ],
        "status": "Vendor Confirmed", "risk": 0
    },
    {
        "vendor_name": "Office Depot India", "invoice_number": "ODI-2026-3001",
        "date": "2026-05-10", "due": "2026-05-25", "subtotal": "9400", "tax": "1692", "total": "11092",
        "items": [
            {"desc": "A4 Paper Ream", "qty": 20, "rate": 250, "amt": 5000, "cat": "Stationery"},
            {"desc": "Stapler", "qty": 10, "rate": 180, "amt": 1800, "cat": "Stationery"},
            {"desc": "Notebook (200 Pages)", "qty": 15, "rate": 120, "amt": 1800, "cat": "Stationery"},
            {"desc": "Whiteboard Marker", "qty": 10, "rate": 80, "amt": 800, "cat": "Stationery"}
        ],
        "status": "Approved", "risk": 0
    },
    {
        "vendor_name": "Office Depot India", "invoice_number": "ODI-2026-3002",
        "date": "2026-05-12", "due": "2026-05-27", "subtotal": "8950", "tax": "1611", "total": "10561",
        "items": [
            {"desc": "Printer Ink Cartridge HP803 Black", "qty": 5, "rate": 650, "amt": 3250, "cat": "Stationery"},
            {"desc": "Desk Organizer", "qty": 8, "rate": 300, "amt": 2400, "cat": "Stationery"},
            {"desc": "Calculator (12 Digit)", "qty": 6, "rate": 550, "amt": 3300, "cat": "Stationery"}
        ],
        "status": "Vendor Confirmed", "risk": 0
    },
    {
        "vendor_name": "Office Depot India", "invoice_number": "ODI-2026-3003",
        "date": "2026-05-14", "due": "2026-05-29", "subtotal": "2125", "tax": "382.5", "total": "2507.5",
        "items": [
            {"desc": "Ball Pens (Pack of 10)", "qty": 10, "rate": 60, "amt": 600, "cat": "Stationery"},
            {"desc": "File Folder (A4)", "qty": 25, "rate": 25, "amt": 625, "cat": "Stationery"},
            {"desc": "Sticky Notes (3x3)", "qty": 20, "rate": 45, "amt": 900, "cat": "Stationery"}
        ],
        "status": "Vendor Confirmed", "risk": 2
    }
]

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

documents_to_embed = []
faiss_metadata = []

def insert_invoice(data):
    vendor = db_vendors[data["vendor_name"]]
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
        document_id=doc.id, vendor_id=vendor.id, invoice_number=data["invoice_number"],
        invoice_date=data["date"], due_date=data["due"], subtotal=data["subtotal"],
        tax_amount=data["tax"], total_amount=data["total"], department=vendor.department,
        payment_status=pay_status, verification_status=ver_status, risk_score=data.get("risk", 0),
        uploaded_at=datetime.strptime(data["date"], "%Y-%m-%d") + timedelta(days=1)
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    for item in data["items"]:
        db.add(LineItem(invoice_id=inv.id, description=item["desc"], amount=str(item["amt"]), category=item["cat"]))
    
    vendor.total_spent += float(data["total"])
    db.commit()

    chunk_text = generate_faiss_chunk(vendor, data["invoice_number"], data["date"], data["items"], data["subtotal"], data["tax"], data["total"], data.get("risk", 0))
    chunk = DocumentChunk(document_id=doc.id, vendor_id=vendor.id, document_type="invoice", chunk_text=chunk_text)
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    
    documents_to_embed.append(chunk_text)
    faiss_metadata.append(chunk.id)
    return doc, inv

# Insert specific invoices
for inv_data in specific_invoices:
    insert_invoice(inv_data)


# 4. Generate Remaining Invoices (to reach ~45)
print("Generating additional invoices to reach 45...")
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

total_generated = 9
start_date = datetime(2026, 4, 1)
while total_generated < 45:
    v_info = random.choice(extra_vendors)
    date = start_date + timedelta(days=random.randint(0, 50))
    date_str = date.strftime("%Y-%m-%d")
    due_str = (date + timedelta(days=15)).strftime("%Y-%m-%d")
    inv_num = f"{v_info['name'][:3].upper()}-2026-4{total_generated:03d}"
    
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
    insert_invoice(data)
    total_generated += 1


# 5. Insert Intentional Fraud Cases
print("Injecting intentional fraud/anomalies...")

# Duplicate
v_info = extra_vendors[0] # OneBite
data = {
    "vendor_name": "OneBite Hapoli", "invoice_number": "OBH-2026-9999",
    "date": "2026-06-01", "due": "2026-06-15", "subtotal": "5000", "tax": "900", "total": "5900",
    "items": [{"desc": "Team Lunch", "qty": 1, "rate": 5000, "amt": 5000, "cat": "Food"}],
    "status": "Vendor Confirmed", "risk": 8
}
doc1, inv1 = insert_invoice(data)
# duplicate insertion
doc2, inv2 = insert_invoice(data)
inv2.verification_status = "Rejected"
inv2.risk_score = 10
db.commit()

db.add(InsightAlert(
    document_id=doc2.id, alert_type="Duplicate", severity="high",
    message=f"Duplicate invoice detected! Invoice #OBH-2026-9999 already exists.",
    explanation="The system found another invoice with the exact same number, amount, and date from this vendor.",
    confidence_score=98
))
db.commit()

# GST Mismatch
data_gst = {
    "vendor_name": "FreshFarm Dairy", "invoice_number": "FRM-2026-5555",
    "date": "2026-06-02", "due": "2026-06-16", "subtotal": "2000", "tax": "360", "total": "2360",
    "items": [{"desc": "Milk 1L", "qty": 30, "rate": 65, "amt": 1950, "cat": "Dairy"}],
    "status": "Vendor Confirmed", "risk": 7
}
doc3, inv3 = insert_invoice(data_gst)
# Fake the FAISS chunk to have a wrong GSTIN
wrong_gst_chunk = f"FULL INVOICE | Invoice No: FRM-2026-5555\nVendor: FreshFarm Dairy\nGSTIN: 99WRONG1234Z9\nInvoice Date: 2026-06-02\nRisk Score: 7\n--- LINE ITEMS ---\nMilk 1L | Qty: 30 | Rate: 65 | Amount: 1950\n--- TOTALS ---\nSubtotal: 2000\nTotal GST: 360\nGrand Total: 2360\n"
chunk_to_update = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc3.id).first()
chunk_to_update.chunk_text = wrong_gst_chunk
db.commit()

db.add(InsightAlert(
    document_id=doc3.id, alert_type="GST Mismatch", severity="high",
    message="GSTIN mismatch detected.",
    explanation="The GSTIN on the invoice (99WRONG1234Z9) does not match the vendor's registered GSTIN (24AAACF1234F1Z5).",
    confidence_score=95
))
db.commit()

# Bank Mismatch
data_bank = {
    "vendor_name": "METRO Wholesale India", "invoice_number": "MTR-2026-6666",
    "date": "2026-06-03", "due": "2026-06-17", "subtotal": "8000", "tax": "1440", "total": "9440",
    "items": [{"desc": "Supplies", "qty": 1, "rate": 8000, "amt": 8000, "cat": "Supplies"}],
    "status": "Vendor Confirmed", "risk": 8
}
doc4, inv4 = insert_invoice(data_bank)
wrong_bank_chunk = f"FULL INVOICE | Invoice No: MTR-2026-6666\nVendor: METRO Wholesale India\nGSTIN: 27AAACM1234N1Z5\nInvoice Date: 2026-06-03\nBank Details: SCB0999999, IFSC: SCBL0000001\nRisk Score: 8\n--- LINE ITEMS ---\nSupplies | Qty: 1 | Rate: 8000 | Amount: 8000\n--- TOTALS ---\nSubtotal: 8000\nTotal GST: 1440\nGrand Total: 9440\n"
chunk_to_update2 = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc4.id).first()
chunk_to_update2.chunk_text = wrong_bank_chunk
db.commit()

db.add(InsightAlert(
    document_id=doc4.id, alert_type="Bank Mismatch", severity="high",
    message="Bank account mismatch detected.",
    explanation="The bank account on the invoice (SCB0999999) does not match the vendor's registered bank account (SBI0009876). Potential fraud risk.",
    confidence_score=99
))
db.commit()
# 5.5 Insert Business Context Documents
print("Inserting Business Context Documents...")
import os
docs_dir = os.path.join(os.path.dirname(__file__), "data", "business_docs")
if os.path.exists(docs_dir):
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            with open(os.path.join(docs_dir, filename), "r") as f:
                content = f.read()
            doc = Document(filename=filename, status="processed", extraction_method="business_memo")
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            chunk = DocumentChunk(
                document_id=doc.id, 
                vendor_id=None, 
                document_type="business_memo", 
                chunk_text=f"BUSINESS CONTEXT DOCUMENT | File: {filename}\n{content}"
            )
            db.add(chunk)
            db.commit()
            print(f"Inserted {filename} into DB.")

# 6. Rebuild FAISS index
print(f"Rebuilding FAISS index with {len(documents_to_embed)} chunks...")
# We use the correct batch logic
knowledge_engine.rebuild_index_from_db(db)

print("Seeding complete!")
