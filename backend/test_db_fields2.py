from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
items = db.query(models.LineItem).limit(10).all()
if items:
    print("LineItem columns:", [c.name for c in models.LineItem.__table__.columns])
    for it in items:
        d = {c.name: getattr(it, c.name) for c in models.LineItem.__table__.columns}
        print(f"  {d}")

# Check Document model
print("\nDocument model columns:", [c.name for c in models.Document.__table__.columns])
docs = db.query(models.Document).limit(3).all()
for d in docs:
    row = {c.name: str(getattr(d, c.name))[:60] for c in models.Document.__table__.columns if getattr(d, c.name) is not None}
    print(f"  {row}")

# Check Invoice model
print("\nInvoice model columns:", [c.name for c in models.Invoice.__table__.columns])
db.close()
