import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, User, Vendor
from app.core.security import get_password_hash

# Must match database.py config
SQLALCHEMY_DATABASE_URL = "sqlite:///./papermine.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_users():
    db = SessionLocal()
    
    # 1. Create tables just in case they don't exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Add Admin User
    admin = db.query(User).filter(User.email == "admin@papermine.com").first()
    if not admin:
        admin = User(
            email="admin@papermine.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            vendor_id=None
        )
        db.add(admin)
        print("Created admin user: admin@papermine.com / admin123")
        
    # 3. Add CFO User
    cfo = db.query(User).filter(User.email == "cfo@technova.com").first()
    if not cfo:
        cfo = User(
            email="cfo@technova.com",
            hashed_password=get_password_hash("cfo123"),
            role="cfo",
            vendor_id=None
        )
        db.add(cfo)
        print("Created CFO user: cfo@technova.com / cfo123")

    # 4. Add Finance Team User
    finance = db.query(User).filter(User.email == "finance@technova.com").first()
    if not finance:
        finance = User(
            email="finance@technova.com",
            hashed_password=get_password_hash("finance123"),
            role="finance_team",
            vendor_id=None
        )
        db.add(finance)
        print("Created Finance Team: finance@technova.com / finance123")
        
    # 6. Get existing vendors and create users for them
    vendors = db.query(Vendor).all()
    for vendor in vendors:
        email = f"{vendor.name.lower().replace(' ', '')}@vendor.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=get_password_hash("vendor123"),
                role="vendor",
                vendor_id=vendor.id
            )
            db.add(user)
            print(f"Created vendor user: {email} / vendor123")
            
    db.commit()
    db.close()

if __name__ == "__main__":
    seed_users()
