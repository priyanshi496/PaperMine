"""
Lightweight, model-free table reconstruction from already-computed OCR boxes.

Why this exists: PP-StructureV3 loads a separate stack of models (doc
orientation, table classification, table cells detection, table structure
recognition) on top of the OCR models you already have running. On a Mac
M4 with limited RAM for the process, that extra stack is what was causing
the hang. This module gets table structure "for free" out of the OcrLine
records paddle_ocr.py already produces (text + confidence + bounding box) --
no additional model, no additional download, no additional RAM.
"""

from typing import List

HEADER_KEYWORDS = ("description", "goods", "quantity", "qty", "unit", "remarks", "price", "importe", "concepto")


def _cluster_1d(values: List[float], gap_threshold: float) -> List[List[float]]:
    """Groups sorted numeric values into clusters, splitting wherever the
    gap between consecutive values exceeds gap_threshold."""
    if not values:
        return []
    values = sorted(values)
    clusters = [[values[0]]]
    for v in values[1:]:
        if v - clusters[-1][-1] > gap_threshold:
            clusters.append([v])
        else:
            clusters[-1].append(v)
    return clusters


def reconstruct_table_from_lines(
    lines: list,  # list[OcrLine]
    row_tolerance: float = 15,
    col_gap_threshold: float = 40,
) -> List[List[str]]:
    """
    Groups OcrLine boxes into rows (by y-center) and columns (by x-start
    clustering), returning a plain list-of-lists grid -- same shape as
    pdfplumber's extract_tables() output.
    """
    if not lines:
        return []

    # ── Step 1: Slice starting from real table header line ──
    table_start_idx = 0
    for idx, l in enumerate(lines):
        text_lower = l.text.lower()
        if any(kw in text_lower for kw in HEADER_KEYWORDS):
            table_start_idx = idx
            break

    table_lines = lines[table_start_idx:] if table_start_idx > 0 else lines
    if len(table_lines) < 2:
        table_lines = lines

    # ── Step 2: Group rows by y-center ──
    items = sorted(table_lines, key=lambda l: (l.box[1], l.box[0]))
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

    if len(rows) < 2:
        return []

    # ── Step 3: Cluster x-starts for column boundaries ──
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
    grid = []
    for row in rows:
        row_cells = [""] * num_cols
        for line in row:
            c = col_index_for(line.box[0])
            row_cells[c] = (row_cells[c] + " " + line.final_text).strip()
        grid.append(row_cells)

    # ── Step 4: Drop empty sparse columns ──
    if grid:
        non_empty_counts = [sum(1 for r in grid if r[c].strip() != "") for c in range(num_cols)]
        cols_to_keep = [c for c, count in enumerate(non_empty_counts) if count > 0]
        grid = [[row[c] for c in cols_to_keep] for row in grid]

    return grid
