from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api.v1 import upload, documents

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

@app.get("/")
def read_root():
    return {"message": "Welcome to PaperMine API!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
