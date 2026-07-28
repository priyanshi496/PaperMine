import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services.paddle_ocr import process_document
from app.api.deps import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Read file and calculate fingerprint
    file_bytes = await file.read()
    import hashlib
    fingerprint = hashlib.sha256(file_bytes).hexdigest()

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Check for exact file duplicate
    existing_doc = db.query(models.Document).filter(
        models.Document.fingerprint == fingerprint,
        models.Document.status != "error"
    ).first()

    db_document = models.Document(
        filename=file.filename,
        filepath=file_path,
        status="duplicate_file" if existing_doc else "uploaded",
        uploaded_by_id=current_user.id,
        fingerprint=fingerprint
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    if existing_doc:
        print(f"[Upload] Intercepted exact file duplicate. Fingerprint: {fingerprint}")
    else:
        # Trigger OCR in the background ONLY if it's not a duplicate
        background_tasks.add_task(process_document, db_document.id)

    return {"message": "File uploaded successfully", "id": db_document.id, "filename": db_document.filename}

