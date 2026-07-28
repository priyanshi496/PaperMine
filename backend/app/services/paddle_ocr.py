import os
import json
import traceback
from dataclasses import dataclass

# Bypass PaddleX online model source connectivity check on every predict() call
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
# Disable oneDNN (MKL-DNN) to prevent PIR executor crash on CPU environments
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

import fitz  # PyMuPDF
from paddleocr import PaddleOCR
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal
from app.services.regex_extractor import extract_invoice_data
from app.services.structured_extraction import merge_extraction
from app.services.table_reconstruct import reconstruct_table_from_lines
from app.services.ocr_postprocess import postprocess_ocr_lines

# ── Configurable parameters (env vars with sensible defaults) ─────────────
# Override via .env or environment variables to tune without code changes.

LOW_CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_LOW_CONFIDENCE_THRESHOLD", "0.80"))
RETRY_CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_RETRY_CONFIDENCE_THRESHOLD", "0.75"))
NORMAL_RENDER_SCALE = int(os.environ.get("OCR_NORMAL_RENDER_SCALE", "3"))
LOW_RES_RENDER_SCALE = int(os.environ.get("OCR_LOW_RES_RENDER_SCALE", "4"))
DET_LIMIT_SIDE_LEN = int(os.environ.get("OCR_DET_LIMIT_SIDE_LEN", "2560"))

# Detection parameters (faint & dense text adjustments)
DET_DB_THRESH = float(os.environ.get("OCR_DET_DB_THRESH", "0.15"))
DET_DB_BOX_THRESH = float(os.environ.get("OCR_DET_DB_BOX_THRESH", "0.35"))
DET_DB_UNCLIP_RATIO = float(os.environ.get("OCR_DET_DB_UNCLIP_RATIO", "1.6"))

# Upscaling parameters
MIN_UPSIZE_WIDTH = int(os.environ.get("OCR_MIN_UPSIZE_WIDTH", "1500"))
TARGET_UPSIZE_WIDTH = int(os.environ.get("OCR_TARGET_UPSIZE_WIDTH", "2500"))

# Supported image extensions for direct image upload (no PDF conversion needed)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

_ocr_engine = None


def get_ocr_engine():
    """PP-OCRv4 mobile det+rec models -- tuned with lower detection thresholds
    to avoid dropping faint or small text on scanned invoices."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = PaddleOCR(
            use_textline_orientation=True,
            lang='en',
            ocr_version='PP-OCRv4',
            det_limit_side_len=DET_LIMIT_SIDE_LEN,
            det_db_thresh=DET_DB_THRESH,
            det_db_box_thresh=DET_DB_BOX_THRESH,
            det_db_unclip_ratio=DET_DB_UNCLIP_RATIO,
            rec_batch_num=8,            # Batch recognition for speed
            enable_mkldnn=False,
        )
    return _ocr_engine


# ── Data model for a single recognized text line ─────────────────────────────

@dataclass
class OcrLine:
    text: str
    score: float
    box: list  # [x0, y0, x1, y1]
    corrected: str | None = None

    @property
    def final_text(self) -> str:
        return self.corrected if self.corrected is not None else self.text


# ── Image Preprocessing ─────────────────────────────────────────────────────

def _minimal_preprocess(img_path: str) -> str:
    """Lightweight preprocessing applied to ALL images:
      - Auto-orient using EXIF metadata (camera photos are often rotated)
      - Upscale if image is too small (e.g. < 1500px width)
    Returns the (possibly modified) image path."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(img_path)

        # Auto-orient based on EXIF (handles rotated camera photos)
        img = ImageOps.exif_transpose(img)

        # Upscale tiny images to give OCR more pixels to work with
        w, h = img.size
        if w < MIN_UPSIZE_WIDTH:
            scale = TARGET_UPSIZE_WIDTH / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        img.save(img_path)
    except Exception as e:
        print(f"[Minimal Preprocess] Warning: {e}")

    return img_path


def _heavy_preprocess(img_path: str) -> str:
    """Aggressive preprocessing for low-confidence results:
      - Deskew (auto-rotate tilted scans/photos)
      - Denoise (remove camera noise / compression artifacts)
      - Adaptive thresholding (handles uneven lighting, shadows, creases)
      - Sharpening (enhance blurred text edges)
    Returns the path to the enhanced image."""
    import cv2
    import numpy as np

    try:
        img = cv2.imread(img_path)
        if img is None:
            return img_path

        # 1. Convert to grayscale for processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Deskew: detect dominant text angle and rotate to correct
        gray = _deskew(gray)

        # 3. Denoise: remove camera noise and JPEG compression artifacts
        gray = cv2.fastNlMeansDenoising(gray, h=12, templateWindowSize=7, searchWindowSize=21)

        # 4. Adaptive threshold: handles uneven lighting, shadows, fold creases
        # Calculate dynamic block size based on image width (approx 4% of width).
        # Ensures block size is an odd number and at least 51 for high-res images.
        h, w = gray.shape
        block_size = max(51, int(w * 0.04) | 1)  # bitwise OR with 1 ensures it's odd
        
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 15
        )

        # 5. Sharpen: unsharp mask to enhance text edges
        blurred = cv2.GaussianBlur(binary, (0, 0), 2.0)
        sharpened = cv2.addWeighted(binary, 1.5, blurred, -0.5, 0)

        # Save the enhanced image back
        cv2.imwrite(img_path, sharpened)

    except Exception as e:
        print(f"[Heavy Preprocess] Warning: {e}")

    return img_path


def _deskew(gray_img):
    """Detects and corrects rotation/skew in the image using contour analysis."""
    import cv2
    import numpy as np

    try:
        # Detect edges
        edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)

        # Find lines using Hough transform
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                minLineLength=100, maxLineGap=10)
        if lines is None or len(lines) < 5:
            return gray_img

        # Calculate angles of detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 == 0:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Only consider near-horizontal lines (within ±30° of horizontal)
            if abs(angle) < 30:
                angles.append(angle)

        if not angles:
            return gray_img

        # Use median angle to avoid outlier influence
        median_angle = np.median(angles)

        # Only correct if skew is detectable but not too extreme
        if abs(median_angle) < 0.5 or abs(median_angle) > 15:
            return gray_img

        # Rotate to correct the skew
        h, w = gray_img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(gray_img, rotation_matrix, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated

    except Exception:
        return gray_img


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_digital_pdf(pdf_document: fitz.Document, sample_pages: int = 3) -> bool:
    pages_to_check = min(sample_pages, len(pdf_document))
    for i in range(pages_to_check):
        page = pdf_document.load_page(i)
        text = page.get_text("text").strip()
        if len(text) > 50:
            return True
    return False


def _extract_text_direct(pdf_document: fitz.Document) -> list[str]:
    pages = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text("text").strip()
        pages.append(f"--- Page {page_num + 1} ---\n{text}")
    return pages


def _pick_render_scale(page: fitz.Page) -> int:
    """Adaptive resolution, biased toward the cheaper option: only step up
    to LOW_RES_RENDER_SCALE when the source scan is itself low-DPI."""
    images = page.get_images(full=True)
    if not images:
        return NORMAL_RENDER_SCALE

    page_width_pt = page.rect.width
    page_width_in = page_width_pt / 72.0 if page_width_pt else 8.5

    max_img_width_px = 0
    for img in images:
        xref = img[0]
        base_img = page.parent.extract_image(xref)
        max_img_width_px = max(max_img_width_px, base_img.get("width", 0))

    if max_img_width_px == 0:
        return NORMAL_RENDER_SCALE

    effective_dpi = max_img_width_px / page_width_in
    return LOW_RES_RENDER_SCALE if effective_dpi < 150 else NORMAL_RENDER_SCALE


def _is_image_file(filepath: str) -> bool:
    """Returns True if the file is a directly-uploadable image (not a PDF)."""
    _, ext = os.path.splitext(filepath.lower())
    return ext in IMAGE_EXTENSIONS


def _lines_from_ocr_result(ocr_result: dict) -> list[OcrLine]:
    texts = ocr_result.get('rec_texts', [])
    boxes = ocr_result.get('rec_boxes', [])
    scores = ocr_result.get('rec_scores', [1.0] * len(texts))
    return [OcrLine(text=t, score=float(s), box=list(b)) for t, b, s in zip(texts, boxes, scores)]


def _avg_confidence(lines: list[OcrLine]) -> float:
    """Returns the average OCR confidence score for a list of lines."""
    if not lines:
        return 0.0
    return sum(l.score for l in lines) / len(lines)


def _reconstruct_text(lines: list[OcrLine], row_tolerance: int = 15, space_gap: int = 10) -> str:
    if not lines:
        return ""
    items = sorted(lines, key=lambda l: ((l.box[1] + l.box[3]) / 2, l.box[0]))
    rows, current_row, row_y = [], [], None
    for line in items:
        y_center = (line.box[1] + line.box[3]) / 2
        if row_y is not None and abs(y_center - row_y) > row_tolerance:
            rows.append(current_row)
            current_row = []
            row_y = y_center
        elif row_y is None:
            row_y = y_center
        current_row.append(line)
    if current_row:
        rows.append(current_row)

    out_lines = []
    for row in rows:
        row.sort(key=lambda l: l.box[0])
        out_lines.append(" ".join(line.final_text for line in row))
    return "\n".join(out_lines)


def _reconstruct_text_grid(lines: list[OcrLine], row_tolerance: int = 15, col_gap_threshold: int = 15) -> str:
    """Formats OCR raw lines into a column-aligned Markdown table representation
    to preserve spatial layout for both the LLM and the frontend view."""
    from app.services.table_reconstruct import _cluster_1d
    if not lines:
        return ""
    
    # 1. Group rows by y-center
    items = sorted(lines, key=lambda l: ((l.box[1] + l.box[3]) / 2, l.box[0]))
    rows, current_row, row_y = [], [], None
    for line in items:
        y_center = (line.box[1] + line.box[3]) / 2
        if row_y is not None and abs(y_center - row_y) > row_tolerance:
            rows.append(current_row)
            current_row = []
            row_y = y_center
        elif row_y is None:
            row_y = y_center
        current_row.append(line)
    if current_row:
        rows.append(current_row)

    if not rows:
        return ""

    # 2. Cluster x-centers for column boundaries
    all_x_centers = [(line.box[0] + line.box[2]) / 2 for row in rows for line in row]
    col_clusters = _cluster_1d(all_x_centers, col_gap_threshold)
    col_boundaries = [min(c) for c in col_clusters]

    def col_index_for(x_center: float) -> int:
        idx = 0
        for i, boundary in enumerate(col_boundaries):
            if x_center >= boundary - 1:
                idx = i
        return idx

    num_cols = len(col_boundaries)
    md_lines = []
    for row in rows:
        row_cells = [""] * num_cols
        for line in row:
            x_center = (line.box[0] + line.box[2]) / 2
            c = col_index_for(x_center)
            row_cells[c] = (row_cells[c] + " " + line.final_text).strip()
        md_lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(md_lines)


# ── OCR Execution (adaptive two-pass) ────────────────────────────────────────

def _run_ocr_on_image(ocr, img_path: str) -> list[OcrLine]:
    """Runs PaddleOCR on a single image file, returns list of OcrLine."""
    page_lines: list[OcrLine] = []
    result = ocr.predict(img_path)
    for ocr_result in result:
        page_lines.extend(_lines_from_ocr_result(ocr_result))
    return page_lines


def _ocr_single_image_adaptive(ocr, img_path: str) -> list[OcrLine]:
    """Two-pass adaptive OCR for a single image:
      Pass 1: Minimal preprocessing → OCR → check confidence
      Pass 2 (if needed): Heavy preprocessing → OCR → pick best result
    """
    # Pass 1: Minimal preprocessing only
    _minimal_preprocess(img_path)
    lines_pass1 = _run_ocr_on_image(ocr, img_path)
    avg_conf_1 = _avg_confidence(lines_pass1)

    if avg_conf_1 >= RETRY_CONFIDENCE_THRESHOLD:
        # Good enough — skip expensive heavy preprocessing
        print(f"  [OCR] Pass 1 confidence: {avg_conf_1:.3f} (≥ {RETRY_CONFIDENCE_THRESHOLD}) — accepted")
        return lines_pass1

    # Pass 2: Heavy preprocessing and retry
    print(f"  [OCR] Pass 1 confidence: {avg_conf_1:.3f} (< {RETRY_CONFIDENCE_THRESHOLD}) — retrying with heavy preprocessing...")
    _heavy_preprocess(img_path)
    lines_pass2 = _run_ocr_on_image(ocr, img_path)
    avg_conf_2 = _avg_confidence(lines_pass2)
    print(f"  [OCR] Pass 2 confidence: {avg_conf_2:.3f}")

    # Pick whichever pass had better confidence
    if avg_conf_2 >= avg_conf_1:
        return lines_pass2
    else:
        print(f"  [OCR] Pass 1 was better ({avg_conf_1:.3f} > {avg_conf_2:.3f}), using Pass 1 results")
        return lines_pass1


def _ocr_pages(pdf_document: fitz.Document, document_id: int) -> list[list[OcrLine]]:
    """Single OCR pass per page. Its output feeds BOTH the text
    reconstruction and the table reconstruction below -- no second model."""
    ocr = get_ocr_engine()
    pages_lines: list[list[OcrLine]] = []

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        scale = _pick_render_scale(page)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

        temp_image_path = f"temp_page_{document_id}_{page_num}.png"
        pix.save(temp_image_path)

        try:
            page_lines = _ocr_single_image_adaptive(ocr, temp_image_path)
            # Apply post-processing (gibberish detection, char fixes, confidence tagging)
            page_lines = postprocess_ocr_lines(page_lines)
            pages_lines.append(page_lines)
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    return pages_lines


def _ocr_image_file(filepath: str, document_id: int) -> list[list[OcrLine]]:
    """OCR for directly-uploaded image files (JPEG/PNG/etc).
    Skips PDF rendering entirely — works directly on the original image."""
    import shutil
    ocr = get_ocr_engine()

    # Work on a copy so preprocessing doesn't modify the original upload
    temp_image_path = f"temp_img_{document_id}{os.path.splitext(filepath)[1]}"
    shutil.copy2(filepath, temp_image_path)

    try:
        page_lines = _ocr_single_image_adaptive(ocr, temp_image_path)
        # Apply post-processing
        page_lines = postprocess_ocr_lines(page_lines)
        return [page_lines]  # Single "page" for an image file
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)


# ── LLM correction (confidence-gated, unchanged) ──────────────────────────────

def call_llm_correction(text: str, context: str) -> str:
    raise NotImplementedError("Wire this to your OpenRouter/Nemotron client")


def apply_low_confidence_correction(pages_lines, threshold: float = LOW_CONFIDENCE_THRESHOLD) -> int:
    corrected_count = 0
    for page_lines in pages_lines:
        for i, line in enumerate(page_lines):
            if line.score >= threshold:
                continue
            neighbors = page_lines[max(0, i - 1):i] + page_lines[i + 1:i + 2]
            context = " ".join(n.text for n in neighbors)
            try:
                line.corrected = call_llm_correction(line.text, context)
                corrected_count += 1
            except NotImplementedError:
                pass
            except Exception as e:
                print(f"[LLM correction] failed on '{line.text}': {e}")
    return corrected_count


# ── Main entry point ──────────────────────────────────────────────────────────

def process_document(document_id: int):
    """
    Pipeline (all on lightweight models -- safe on limited-RAM machines):
      1. Detect file type (image vs PDF) and digital vs. scanned.
      2. Digital PDF  -> PyMuPDF text, pdfplumber tables (unchanged, cheap).
      3. Scanned PDF / Image  -> Adaptive two-pass PP-OCRv4 with preprocessing
                                -> Post-processing (gibberish detection, char fixes)
                                -> raw text (saved immediately)
                                -> table reconstructed from the SAME OCR boxes
                                -> optional low-confidence LLM fix.
      4. India-specific regex field extraction (GSTIN, invoice no, CGST/SGST/IGST).
    """
    db: Session = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        filepath = doc.filepath
        if not os.path.exists(filepath):
            doc.status = "error"
            db.commit()
            return

        # ── Route based on file type ──
        is_image = _is_image_file(filepath)
        is_digital = False
        pdf_document = None

        if is_image:
            # Direct image file — always OCR path
            print(f"[Document {document_id}] Image file detected ({os.path.splitext(filepath)[1]}) -- using PaddleOCR (PP-OCRv4) with adaptive preprocessing.")
            doc.extraction_method = "ocr"

            pages_lines = _ocr_image_file(filepath, document_id)

        else:
            # PDF file — detect digital vs scanned
            pdf_document = fitz.open(filepath)
            is_digital = _is_digital_pdf(pdf_document)

            if is_digital:
                print(f"[Document {document_id}] Digital PDF detected -- using PyMuPDF (no OCR).")
                doc.extraction_method = "direct"
                final_text = "\n\n".join(_extract_text_direct(pdf_document))
                doc.ocr_text = final_text
                pdf_document.close()
                db.commit()
            else:
                print(f"[Document {document_id}] Scanned/image PDF detected -- using PaddleOCR (PP-OCRv4) with adaptive preprocessing.")
                doc.extraction_method = "ocr"

                pages_lines = _ocr_pages(pdf_document, document_id)
                pdf_document.close()

        # ── Process OCR results (for both image and scanned PDF paths) ──
        if not is_digital:
            # Clean spaced text for human viewing in the UI
            user_pages = [
                f"--- Page {i + 1} ---\n{_reconstruct_text(lines)}"
                for i, lines in enumerate(pages_lines)
            ]
            doc.ocr_text = "\n\n".join(user_pages)

            # Structured grid representation to help the LLM align column data
            grid_pages = [
                f"--- Page {i + 1} ---\n{_reconstruct_text_grid(lines)}"
                for i, lines in enumerate(pages_lines)
            ]
            final_text = "\n\n".join(grid_pages)
            db.commit()

            doc.status = "correcting_low_confidence"
            db.commit()
            n_corrected = apply_low_confidence_correction(pages_lines)
            if n_corrected > 0:
                # Update human-viewable corrected text
                user_corrected = [
                    f"--- Page {i + 1} ---\n{_reconstruct_text(lines)}"
                    for i, lines in enumerate(pages_lines)
                ]
                doc.corrected_text = "\n\n".join(user_corrected)

                # Update LLM corrected grid text
                grid_corrected = [
                    f"--- Page {i + 1} ---\n{_reconstruct_text_grid(lines)}"
                    for i, lines in enumerate(pages_lines)
                ]
                final_text = "\n\n".join(grid_corrected)
                db.commit()

        # Step 3: Structured field + table extraction. merge_extraction reconciles
        # regex (deterministic, checksummed -- GSTIN, invoice no, dates, amounts)
        # with the LLM (free text + table) field-by-field: regex wins whenever it
        # found a value, LLM only fills gaps regex has no concept of. Every field
        # is stored as {value, source, confidence}, not a bare value, so a wrong
        # LLM guess never silently overrides a correct checksummed regex value.
        structured = None
        try:
            structured = merge_extraction(final_text)
            doc.summary = json.dumps(structured)
            db.commit()
            found = {k: v["value"] for k, v in structured.items() if v["value"] is not None}
            print(f"[Document {document_id}] Extracted fields: {found}")

            llm_table = (structured.get("table") or {}).get("value") or []
            if llm_table:
                db.query(models.Table).filter(models.Table.document_id == document_id).delete()
                db.add(models.Table(document_id=document_id, page=1, json_data=json.dumps(llm_table)))
                db.commit()
        except Exception as e:
            print(f"[Document {document_id}] Field extraction error: {e}")

        # Table fallback chain -- only runs if the LLM step above didn't already
        # produce a table (e.g. the LLM call itself failed, not just one field
        # being null): pdfplumber/PP-StructureV3 first, then local OCR-box
        # reconstruction as the last resort for scanned borderless docs.
        doc.status = "extracting_tables"
        db.commit()
        have_table = db.query(models.Table).filter(models.Table.document_id == document_id).count() > 0
        if not have_table:
            from app.services.table_extractor import extract_tables, _clean_and_structure_table

            if not is_image:
                extract_tables(document_id, filepath, is_digital=is_digital)
            db.commit()

            have_table = db.query(models.Table).filter(models.Table.document_id == document_id).count() > 0
            if not is_digital and not have_table:
                print(f"[Document {document_id}] Falling back to local OCR box reconstruction...")
                for page_num, lines in enumerate(pages_lines):
                    grid = reconstruct_table_from_lines(lines)
                    cleaned_grid = _clean_and_structure_table(grid)
                    if cleaned_grid:
                        db.add(models.Table(
                            document_id=document_id,
                            page=page_num + 1,
                            json_data=json.dumps(cleaned_grid),
                        ))
                db.commit()

        doc.status = "processed"
        db.commit()

    except Exception as e:
        print(f"[Document {document_id}] Processing error: {e}")
        traceback.print_exc()
        try:
            doc.status = "error"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _data_summary(d: dict) -> str:
    parts = [f"{k}={v}" for k, v in d.items() if v is not None]
    return ", ".join(parts) if parts else "No fields extracted"