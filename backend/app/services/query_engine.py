"""
query_engine.py

Replaces the growing "one template per phrasing" registry with a small,
composable query plan that the LLM fills in and this module executes
safely. New question phrasings become new COMBINATIONS of filters /
aggregation / sort / limit — not new named templates and not new code.

Design goals:
- Whitelisted fields and operators only. The LLM never writes SQL or code,
  it fills in a constrained JSON structure, so there's no injection risk
  and no way to reference a column/table that doesn't exist.
- One executor handles counts, sums, averages, min/max, filtered lists,
  and "list + attached line items" — the shapes that used to require a
  dozen near-duplicate template functions.
- Amount fields (total_amount, amount) are stored as strings in this
  schema, so filtering/sorting/aggregating on them happens in Python via
  clean_amount() after a cheap DB-level fetch on the other filters. If you
  later migrate these columns to Numeric, swap the amount-handling block
  for real SQL — the plan schema itself doesn't need to change.

Query Plan schema (what the LLM must emit for route == "DATABASE"):
{
  "type": "aggregate" | "list",
  "entity": "invoice" | "line_item" | "alert",
  "filters": [
      {"field": "total_amount", "op": ">", "value": 1800},
      {"field": "line_item.description", "op": "contains", "value": "coffee"}
  ],
  "aggregate_fn": "sum" | "avg" | "count" | "min" | "max" | null,
  "aggregate_field": "total_amount" | "amount" | null,
  "group_by": "description" | null,
  "sort_field": "total_amount" | null,
  "sort_dir": "asc" | "desc" | null,
  "limit": 1-50 | null,
  "include_items": true | false
}
"""

from typing import Optional, List, Dict, Any
from app.db import models
from app.services.financial_utils import clean_amount

MAX_LIMIT = 50

# ---------------------------------------------------------------------------
# Whitelists — the ONLY fields/ops the plan is allowed to reference.
# ---------------------------------------------------------------------------

INVOICE_SQL_FIELDS = {
    # field_name -> (ORM column, value_type)
    "vendor_id": (models.Invoice.vendor_id, "number"),
    "risk_score": (models.Invoice.risk_score, "number"),
    "verification_status": (models.Invoice.verification_status, "text"),
    "invoice_number": (models.Invoice.invoice_number, "text"),
    "invoice_date": (models.Invoice.invoice_date, "text"),
}
INVOICE_AMOUNT_FIELDS = {"total_amount", "tax_amount"}  # handled in Python

LINE_ITEM_SQL_FIELDS = {
    "description": (models.LineItem.description, "text"),
    "category": (models.LineItem.category, "text"),
}
LINE_ITEM_AMOUNT_FIELDS = {"amount"}  # handled in Python

ALERT_SQL_FIELDS = {
    "alert_type": (models.InsightAlert.alert_type, "text"),
    "severity": (models.InsightAlert.severity, "text"),
}

CROSS_FIELDS = {"line_item.description", "line_item.category"}  # only valid when entity == "invoice"

ALLOWED_OPS = {">", "<", ">=", "<=", "==", "!=", "contains"}
ALLOWED_AGG_FNS = {"sum", "avg", "count", "min", "max"}


class QueryPlanError(Exception):
    pass


def validate_plan(plan: Dict[str, Any]) -> None:
    if plan.get("entity") not in ("invoice", "line_item", "alert"):
        raise QueryPlanError(f"Unknown entity: {plan.get('entity')}")
    if plan.get("type") not in ("aggregate", "list"):
        raise QueryPlanError(f"Unknown query type: {plan.get('type')}")
    if plan.get("aggregate_fn") is not None and plan["aggregate_fn"] not in ALLOWED_AGG_FNS:
        raise QueryPlanError(f"Unknown aggregate_fn: {plan.get('aggregate_fn')}")
    for f in plan.get("filters", []):
        if f.get("op") not in ALLOWED_OPS:
            raise QueryPlanError(f"Unknown operator: {f.get('op')}")


def _field_lookup(entity: str, field: str):
    """Returns (kind, column_or_none) where kind in {'sql', 'amount', 'cross'}."""
    if entity == "invoice":
        if field in INVOICE_SQL_FIELDS:
            return "sql", INVOICE_SQL_FIELDS[field][0]
        if field in INVOICE_AMOUNT_FIELDS:
            return "amount", field
        if field in CROSS_FIELDS:
            return "cross", field
    elif entity == "line_item":
        if field in LINE_ITEM_SQL_FIELDS:
            return "sql", LINE_ITEM_SQL_FIELDS[field][0]
        if field in LINE_ITEM_AMOUNT_FIELDS:
            return "amount", field
    elif entity == "alert":
        if field in ALERT_SQL_FIELDS:
            return "sql", ALERT_SQL_FIELDS[field][0]
    raise QueryPlanError(f"Field '{field}' is not allowed for entity '{entity}'")


def _apply_sql_filter(query, column, op, value, value_type):
    if op == "contains":
        return query.filter(column.ilike(f"%{value}%"))
    if value_type == "text":
        # Case-insensitive equality by default — statuses like
        # "Verified"/"verified" shouldn't be a matching footgun.
        if op == "==":
            return query.filter(column.ilike(str(value)))
        if op == "!=":
            return query.filter(~column.ilike(str(value)) | column.is_(None))
        raise QueryPlanError(f"Operator '{op}' not supported for text field")
    # numeric column (e.g. risk_score, vendor_id)
    if op == ">":
        return query.filter(column > value)
    if op == "<":
        return query.filter(column < value)
    if op == ">=":
        return query.filter(column >= value)
    if op == "<=":
        return query.filter(column <= value)
    if op == "==":
        return query.filter(column == value)
    if op == "!=":
        return query.filter(column != value)
    raise QueryPlanError(f"Unsupported operator '{op}'")


def _passes_amount_filter(amount: Optional[float], op: str, value) -> bool:
    if amount is None:
        return False
    value = float(value)
    return {
        ">": amount > value, "<": amount < value,
        ">=": amount >= value, "<=": amount <= value,
        "==": abs(amount - value) < 0.01, "!=": abs(amount - value) >= 0.01,
    }.get(op, False)


def execute_query_plan(db, plan: Dict[str, Any], vendor_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Executes a validated query plan and returns a structured result dict
    for the formatter to render. Never returns raw SQL/ORM objects to the
    caller beyond what's needed for formatting.
    """
    validate_plan(plan)
    entity = plan["entity"]

    # --- Base query + vendor scoping ---
    if entity == "invoice":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
    elif entity == "line_item":
        q = db.query(models.LineItem).join(models.Invoice, models.Invoice.id == models.LineItem.invoice_id)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
    elif entity == "alert":
        q = db.query(models.InsightAlert)
        if vendor_id:
            q = q.join(models.Invoice, models.Invoice.document_id == models.InsightAlert.document_id)
            q = q.filter(models.Invoice.vendor_id == vendor_id)

    amount_filters = []       # applied in Python after fetch
    cross_filters = []        # applied via EXISTS subquery

    for f in plan.get("filters", []):
        kind, ref = _field_lookup(entity, f["field"])
        if kind == "sql":
            _, value_type = (
                INVOICE_SQL_FIELDS.get(f["field"]) or
                LINE_ITEM_SQL_FIELDS.get(f["field"]) or
                ALERT_SQL_FIELDS.get(f["field"])
            )
            q = _apply_sql_filter(q, ref, f["op"], f["value"], value_type)
        elif kind == "amount":
            amount_filters.append((ref, f["op"], f["value"]))
        elif kind == "cross":
            cross_filters.append(f)

    # Cross-entity filters (only meaningful for entity == "invoice"):
    # "does this invoice have a line item matching X"
    for f in cross_filters:
        sub_field = f["field"].split(".", 1)[1]  # "description" or "category"
        column = LINE_ITEM_SQL_FIELDS[sub_field][0]
        matching_invoice_ids = [
            row[0] for row in
            db.query(models.LineItem.invoice_id).filter(column.ilike(f"%{f['value']}%")).all()
        ]
        q = q.filter(models.Invoice.id.in_(matching_invoice_ids)) if matching_invoice_ids else q.filter(False)

    rows = q.all()

    # Apply amount-based filters in Python (columns are strings in this schema)
    def get_amount(row, field):
        raw = getattr(row, field, None)
        return clean_amount(raw)

    for field, op, value in amount_filters:
        rows = [r for r in rows if _passes_amount_filter(get_amount(r, field), op, value)]

    skipped_unparseable = 0

    # --- Aggregate mode ---
    if plan["type"] == "aggregate":
        agg_field = plan.get("aggregate_field")
        agg_fn = plan["aggregate_fn"]

        if agg_fn == "count":
            group_by = plan.get("group_by")
            if group_by and entity == "line_item":
                groups: Dict[str, Dict[str, Any]] = {}
                for r in rows:
                    key = getattr(r, group_by, "Unknown") or "Unknown"
                    groups.setdefault(key, {"count": 0})
                    groups["count"] = groups[key]["count"] + 1  # noqa (kept simple)
                return {"type": "aggregate", "fn": "count", "value": len(rows), "groups": None}
            return {"type": "aggregate", "fn": "count", "value": len(rows)}

        values = []
        for r in rows:
            val = get_amount(r, agg_field) if agg_field in (INVOICE_AMOUNT_FIELDS | LINE_ITEM_AMOUNT_FIELDS) else getattr(r, agg_field, None)
            if val is None:
                skipped_unparseable += 1
            else:
                values.append(float(val))

        if not values:
            return {"type": "aggregate", "fn": agg_fn, "value": None, "skipped": skipped_unparseable}

        result_value = {
            "sum": sum(values), "avg": sum(values) / len(values),
            "min": min(values), "max": max(values),
        }[agg_fn]

        # Optional grouping for e.g. "spending on coffee, broken down by item"
        group_by = plan.get("group_by")
        groups_out = None
        if group_by and entity == "line_item":
            groups: Dict[str, Dict[str, float]] = {}
            for r in rows:
                val = get_amount(r, agg_field)
                if val is None:
                    continue
                key = (getattr(r, group_by, None) or "Unknown").strip()
                groups.setdefault(key, {"total": 0.0, "count": 0})
                groups[key]["total"] += val
                groups[key]["count"] += 1
            groups_out = groups

        return {
            "type": "aggregate", "fn": agg_fn, "value": result_value,
            "skipped": skipped_unparseable, "groups": groups_out,
        }

    # --- List mode ---
    sort_field = plan.get("sort_field")
    sort_dir = plan.get("sort_dir", "desc")
    if sort_field:
        is_amount = sort_field in (INVOICE_AMOUNT_FIELDS | LINE_ITEM_AMOUNT_FIELDS)
        rows.sort(
            key=lambda r: (get_amount(r, sort_field) if is_amount else getattr(r, sort_field, None)) or 0,
            reverse=(sort_dir == "desc"),
        )

    limit = min(plan.get("limit") or MAX_LIMIT, MAX_LIMIT)
    rows = rows[:limit]

    items_by_invoice = {}
    if plan.get("include_items") and entity == "invoice":
        invoice_ids = [r.id for r in rows]
        if invoice_ids:
            all_items = db.query(models.LineItem).filter(models.LineItem.invoice_id.in_(invoice_ids)).all()
            for it in all_items:
                items_by_invoice.setdefault(it.invoice_id, []).append(it)

    return {"type": "list", "rows": rows, "entity": entity, "items_by_invoice": items_by_invoice}


def format_query_result(plan: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Turns an execute_query_plan() result into a user-facing markdown answer."""
    if result["type"] == "aggregate":
        fn, value = result["fn"], result["value"]
        skipped_note = f" _( {result['skipped']} record(s) had unparseable amounts and were excluded.)_" if result.get("skipped") else ""

        if fn == "count":
            return f"Count: **{value}**"
        if value is None:
            return "No matching records with a parseable amount were found."

        label = {"sum": "Total", "avg": "Average", "min": "Minimum", "max": "Maximum"}[fn]
        base = f"{label}: **₹{value:,.2f}**{skipped_note}"

        if result.get("groups"):
            lines = [f"- {k}: ₹{v['total']:,.2f} ({v['count']} item(s))" for k, v in result["groups"].items()]
            base += "\n\n**Breakdown:**\n" + "\n".join(lines)
        return base

    # list mode
    rows = result["rows"]
    if not rows:
        return "No matching records found."

    entity = result["entity"]
    lines = []
    for r in rows:
        if entity == "invoice":
            amt = clean_amount(r.total_amount) or 0.0
            lines.append(f"- Invoice **{r.invoice_number}**: ₹{amt:,.2f}")
            if r.id in result.get("items_by_invoice", {}):
                for it in result["items_by_invoice"][r.id]:
                    item_amt = clean_amount(it.amount) or 0.0
                    lines.append(f"    - {it.description}: ₹{item_amt:,.2f}")
        elif entity == "line_item":
            amt = clean_amount(r.amount) or 0.0
            lines.append(f"- {r.description}: ₹{amt:,.2f}")
        elif entity == "alert":
            lines.append(f"- [{r.alert_type}] {r.message}")

    return "\n".join(lines)
