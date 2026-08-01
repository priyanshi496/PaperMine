from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api.v1 import upload, documents, insights, invoices, auth

# Create database tables (idempotent — does NOT drop existing data)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PaperMine API",
    description="Backend API for PaperMine OCR application",
    version="1.0.0",
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["insights"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
from app.api.v1 import dashboard
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
from app.api.v1 import assistant
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["assistant"])

from app.api.v1 import vendors
app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["vendors"])

@app.get("/")
def read_root():
    return {"message": "Welcome to PaperMine API!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Trigger reload
