import os
import json
import traceback
from dataclasses import dataclass

# Bypass PaddleX online model source connectivity check on every predict() call
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import fitz  # PyMuPDF
from paddleocr import PaddleOCR
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal
from app.services.regex_extractor import extract_invoice_data
from app.services.structured_extraction import merge_extraction
from app.services.table_reconstruct import reconstruct_table_from_lines

# ── Config ─────────────────────────────────────────────────────────────────
# Deliberately light: no PP-StructureV3 (multi-model stack that hangs on
# limited-RAM machines), no v6 server models (GPU-oriented). Everything here
# runs on the ONE mobile OCR model already loaded for text extraction --
# tables are reconstructed from its output, not from a second model.

LOW_CONFIDENCE_THRESHOLD = 0.80
NORMAL_RENDER_SCALE = 3       # Step up to 3x for camera photos/small print receipts
LOW_RES_RENDER_SCALE = 4      # Step up to 4x for low-DPI scans

_ocr_engine = None


def get_ocr_engine():
    """PP-OCRv4 mobile det+rec models -- configured with higher detection side limits
    to recognize small fonts and side details on camera receipts."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = PaddleOCR(
            use_textline_orientation=True,
            lang='en',
            ocr_version='PP-OCRv4',
            det_limit_side_len=1500,  # Increase max side length to preserve small text details
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


def _lines_from_ocr_result(ocr_result: dict) -> list[OcrLine]:
    texts = ocr_result.get('rec_texts', [])
    boxes = ocr_result.get('rec_boxes', [])
    scores = ocr_result.get('rec_scores', [1.0] * len(texts))
    return [OcrLine(text=t, score=float(s), box=list(b)) for t, b, s in zip(texts, boxes, scores)]


def _reconstruct_text(lines: list[OcrLine], row_tolerance: int = 15, space_gap: int = 10) -> str:
    if not lines:
        return ""
    items = sorted(lines, key=lambda l: (l.box[1], l.box[0]))
    rows, current_row, last_y = [], [], None
    for line in items:
        y_center = (line.box[1] + line.box[3]) / 2
        if last_y is not None and abs(y_center - last_y) > row_tolerance:
            rows.append(current_row)
            current_row = []
        current_row.append(line)
        last_y = y_center
    if current_row:
        rows.append(current_row)

    out_lines = []
    for row in rows:
        row.sort(key=lambda l: l.box[0])
        parts, prev_x_end = [], None
        for line in row:
            if prev_x_end is not None and (line.box[0] - prev_x_end) > space_gap:
                parts.append(" ")
            parts.append(line.final_text)
            prev_x_end = line.box[2]
        out_lines.append("".join(parts))
    return "\n".join(out_lines)


def _reconstruct_text_grid(lines: list[OcrLine], row_tolerance: int = 15, col_gap_threshold: int = 35) -> str:
    """Formats OCR raw lines into a column-aligned Markdown table representation
    to preserve spatial layout for both the LLM and the frontend view."""
    from app.services.table_reconstruct import _cluster_1d
    if not lines:
        return ""
    
    # 1. Group rows by y-center
    items = sorted(lines, key=lambda l: (l.box[1], l.box[0]))
    rows, current_row, last_y = [], [], None
    for line in items:
        y_center = (line.box[1] + line.box[3]) / 2
        if last_y is not None and abs(y_center - last_y) > row_tolerance:
            rows.append(current_row)
            current_row = []
        current_row.append(line)
        last_y = y_center
    if current_row:
        rows.append(current_row)

    if not rows:
        return ""

    # 2. Cluster x-starts for column boundaries
    all_x_starts = [line.box[0] for row in rows for line in row]
    col_clusters = _cluster_1d(all_x_starts, col_gap_threshold)
    col_boundaries = [min(c) for c in col_clusters]

    def col_index_for(x: float) -> int:
        idx = 0
        for i, boundary in enumerate(col_boundaries):
            if x >= boundary - 1:
                idx = i
        return idx

    num_cols = len(col_boundaries)
    md_lines = []
    for row in rows:
        row_cells = [""] * num_cols
        for line in row:
            c = col_index_for(line.box[0])
            row_cells[c] = (row_cells[c] + " " + line.final_text).strip()
        md_lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(md_lines)



def _enhance_image(img_path: str):
    """
    Enhances contrast and removes uneven lighting/shadows using OpenCV CLAHE.
    This helps PaddleOCR read tiny print and text cut by creases/folds.
    """
    import cv2
    try:
        img = cv2.imread(img_path)
        if img is None:
            return
        # Convert to gray
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        # Save the enhanced image back
        cv2.imwrite(img_path, enhanced)
    except Exception as e:
        print(f"[Image Enhancement] Error: {e}")


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

        # Apply image contrast/shadow enhancement before running OCR
        _enhance_image(temp_image_path)

        try:
            result = ocr.predict(temp_image_path)
            page_lines: list[OcrLine] = []
            for ocr_result in result:
                page_lines.extend(_lines_from_ocr_result(ocr_result))
            pages_lines.append(page_lines)
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    return pages_lines


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
      1. Detect digital vs. scanned.
      2. Digital  -> PyMuPDF text, pdfplumber tables (unchanged, cheap).
      3. Scanned  -> ONE PP-OCRv4-mobile pass -> raw text (saved immediately)
                      -> table reconstructed from the SAME OCR boxes (no
                         second model) -> optional low-confidence LLM fix.
      4. India-specific regex field extraction (GSTIN, invoice no, CGST/SGST/IGST).
    """
    db: Session = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        pdf_path = doc.filepath
        if not os.path.exists(pdf_path):
            doc.status = "error"
            db.commit()
            return

        pdf_document = fitz.open(pdf_path)
        is_digital = _is_digital_pdf(pdf_document)

        if is_digital:
            print(f"[Document {document_id}] Digital PDF detected -- using PyMuPDF (no OCR).")
            doc.extraction_method = "direct"
            final_text = "\n\n".join(_extract_text_direct(pdf_document))
            doc.ocr_text = final_text
            pdf_document.close()
            db.commit()
        else:
            print(f"[Document {document_id}] Scanned/image PDF detected -- using PaddleOCR (PP-OCRv4 mobile).")
            doc.extraction_method = "ocr"

            pages_lines = _ocr_pages(pdf_document, document_id)
            pdf_document.close()

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
            extract_tables(document_id, pdf_path, is_digital=is_digital)
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