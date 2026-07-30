"""Inspect all DB fields available for every invoice."""
from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
invs = db.query(models.Invoice).all()
for inv in invs:
    print(f"\n=== Invoice {inv.invoice_number} ===")
    for col in models.Invoice.__table__.columns:
        val = getattr(inv, col.name)
        if val is not None:
            print(f"  {col.name}: {str(val)[:80]}")

# Check InsightAlert table
print("\n=== ALERTS ===")
alerts = db.query(models.InsightAlert).all()
print(f"Total alerts: {len(alerts)}")
for a in alerts[:3]:
    print(f"  type={a.alert_type} severity={a.severity} msg={str(a.message)[:80]}")

# Check Vendor table
print("\n=== VENDORS ===")
vendors = db.query(models.Vendor).all()
for v in vendors:
    print(f"  id={v.id} name={v.name}")
    for col in models.Vendor.__table__.columns:
        val = getattr(v, col.name)
        if val is not None:
            print(f"    {col.name}: {str(val)[:60]}")

# Check LineItem table
print("\n=== LINE ITEMS (sample) ===")
items = db.query(models.LineItem).limit(5).all()
for it in items:
    print(f"  inv_id={it.invoice_id} desc={it.description} qty={it.quantity} amt={it.amount} cat={it.category}")

db.close()
