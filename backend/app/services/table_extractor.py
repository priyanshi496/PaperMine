import os
import json
import unicodedata
from io import StringIO
from typing import List, Optional

import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal

# Disable PaddleX online model source check
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

LINE_ITEM_HEADERS = {
    "product": ["description", "descripción", "product", "producto", "item", "concepto", "goods", "description of goods"],
    "quantity": ["qty", "quantity", "cantidad", "cant", "units", "unidades"],
    "unit": ["unit of measure", "unit", "uom", "medida"],
    "gross_price": ["price", "unit price", "precio", "p.u.", "rate", "precio unitario"],
    "base": ["total", "subtotal", "importe", "amount", "base", "total price", "importe neto"],
    "remarks": ["additional remarks", "remarks", "observaciones", "cartons", "packaging"],
}

HEADER_TRIGGER_KEYWORDS = ("description", "goods", "quantity", "qty", "unit of measure", "remarks", "price", "importe", "concepto")
SUMMARY_KEYWORDS = ("subtotal", "total", "iva", "vat", "base imponible", "base amount", "tax", "importe total", "signature", "stamp")

_structure_engine = None


def get_structure_engine():
    """Lazy singleton for PP-StructureV3 with heavy extra models disabled for speed."""
    global _structure_engine
    if _structure_engine is None:
        try:
            from paddleocr import PPStructureV3
            _structure_engine = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_formula_recognition=False,
                use_chart_recognition=False,
                use_seal_recognition=False,
                use_region_detection=False,
            )
        except Exception as e:
            print(f"[Table Extractor] PPStructureV3 init error: {e}")
            _structure_engine = False
    return _structure_engine if _structure_engine is not False else None


def _normalize(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _is_summary_row(row: List[str]) -> bool:
    row_text = _normalize(" ".join(str(c) for c in row if c))
    return any(kw in row_text for kw in SUMMARY_KEYWORDS)


def _clean_and_structure_table(raw_table: List[List[str]]) -> List[List[str]]:
    """
    Post-processes extracted tables:
    1. Finds the true header row (e.g. DESCRIPTION OF GOODS | QUANTITY).
    2. Drops document metadata rows above the line items table.
    3. Merges/deduplicates identical adjacent columns (caused by wide merged headers).
    4. Drops empty or trailing noise columns.
    """
    if not raw_table:
        return []

    # Step 1: Find real header row
    header_idx = -1
    for idx, row in enumerate(raw_table):
        row_norm = _normalize(" ".join(str(c) for c in row if c))
        if any(kw in row_norm for kw in HEADER_TRIGGER_KEYWORDS):
            header_idx = idx
            break

    if header_idx == -1:
        # No table header keyword found -- this is document metadata text, not a line-items table
        return []

    table = raw_table[header_idx:]
    if not table:
        return []

    # Step 2: Remove completely empty rows or footer noise
    clean_rows = []
    for row in table:
        cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(cells):
            continue
        if _is_summary_row(cells):
            continue
        clean_rows.append(cells)

    if not clean_rows:
        return []

    num_cols = max(len(r) for r in clean_rows)
    # Pad rows to uniform length
    padded = [r + [""] * (num_cols - len(r)) for r in clean_rows]

    # Step 3: Remove duplicate adjacent columns
    cols_to_keep = []
    for c in range(num_cols):
        if c > 0:
            # Check similarity between col c and col c-1 across data rows
            matches = sum(1 for r in padded[1:] if _normalize(r[c]) == _normalize(r[c - 1]) and r[c] != "")
            total_non_empty = sum(1 for r in padded[1:] if r[c] != "")
            if total_non_empty > 0 and (matches / total_non_empty) > 0.6:
                # Column c is a duplicate of c-1 (e.g. duplicated Description column), skip it
                continue
        # Check if column is non-empty
        col_text = "".join(_normalize(r[c]) for r in padded)
        if col_text and col_text not in ("-", "—", "none", "null"):
            cols_to_keep.append(c)

    filtered = [[row[c] for c in cols_to_keep] for row in padded]

    # Clean up duplicate text in the header row itself (e.g. ['DESCRIPTION', 'DESCRIPTION', 'QTY'] -> ['DESCRIPTION', 'QTY'])
    if filtered and len(filtered[0]) > 1:
        new_header = []
        for i, h in enumerate(filtered[0]):
            if i > 0 and _normalize(h) == _normalize(filtered[0][i - 1]):
                continue
            new_header.append(h)
        # Pad header if needed
        while len(new_header) < len(filtered[0]):
            new_header.append("")
        filtered[0] = new_header

    return filtered


def extract_tables_digital(pdf_path: str) -> List[List[List[str]]]:
    """Path A: Fast pdfplumber extraction for digital PDFs."""
    extracted = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tbl in tables:
                clean_tbl = [
                    [str(cell).strip() if cell is not None else "" for cell in row]
                    for row in tbl if row
                ]
                processed = _clean_and_structure_table(clean_tbl)
                if processed:
                    extracted.append(processed)
    return extracted


def extract_tables_scanned(pdf_path: str) -> List[List[List[str]]]:
    """Path B: PP-StructureV3 extraction for scanned/image PDFs."""
    engine = get_structure_engine()
    if not engine:
        return []

    doc = fitz.open(pdf_path)
    extracted = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        temp_img_path = f"temp_tab_{page_num}.png"
        pix.save(temp_img_path)

        try:
            output = engine.predict(input=temp_img_path)
            for res in output:
                table_list = res.get("table_res_list", []) if hasattr(res, "get") else getattr(res, "table_res_list", [])
                for table_res in table_list:
                    html = table_res.get("pred_html") if hasattr(table_res, "get") else getattr(table_res, "pred_html", None)
                    if not html:
                        continue
                    try:
                        dfs = pd.read_html(StringIO(html))
                    except Exception:
                        continue

                    for df in dfs:
                        clean_tbl = df.fillna("").astype(str).values.tolist()
                        clean_tbl.insert(0, [str(c) for c in df.columns])
                        processed = _clean_and_structure_table(clean_tbl)
                        if processed:
                            extracted.append(processed)
        finally:
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

    doc.close()
    return extracted


def extract_tables(document_id: int, pdf_path: str, is_digital: bool = True):
    """
    Main entry point for table extraction.
    Uses Path A (pdfplumber) for digital PDFs and Path B (PP-StructureV3) for scanned PDFs.
    """
    db: Session = SessionLocal()
    try:
        if is_digital:
            tables = extract_tables_digital(pdf_path)
        else:
            tables = extract_tables_scanned(pdf_path)

        for page_num, table in enumerate(tables):
            db_table = models.Table(
                document_id=document_id,
                page=page_num + 1,
                json_data=json.dumps(table),
            )
            db.add(db_table)

        db.commit()
        print(f"[Document {document_id}] Saved {len(tables)} table(s) to DB.")
    except Exception as e:
        print(f"[Document {document_id}] Table extraction error: {e}")
        db.rollback()
    finally:
        db.close()
