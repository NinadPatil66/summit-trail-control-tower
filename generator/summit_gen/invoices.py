"""Supplier invoices as PDFs, plus a header CSV and an answer-key label file.

About 3% of invoices bill one line at an older unit cost (planted cause 6).
Your three-way match should catch exactly those.
"""
from datetime import timedelta

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .config import make_rng
from .master import read_master
from .writers import write_csv


def cost_on(history, sku_code, day):
    """Unit cost valid on a day: the latest extract on or before it."""
    rows = history[(history["sku_code"] == sku_code) & (history["extract_date"] <= day.isoformat())]
    return float(rows.iloc[-1]["unit_cost"])


def previous_cost(history, sku_code, day):
    """The cost before the current one, or None if the SKU never changed."""
    rows = history[(history["sku_code"] == sku_code) & (history["extract_date"] <= day.isoformat())]
    distinct = rows["unit_cost"].drop_duplicates()
    return float(distinct.iloc[-2]) if len(distinct) > 1 else None


def build_invoices(products, history, suppliers, cfg, rng):
    start, end = cfg["history"]["start"], cfg["history"]["end"]
    n = cfg["invoices"]["count"]
    stale_count = max(1, round(n * cfg["planted"]["stale_invoice_cost"]["rate"]))
    stale_ids = set(rng.choice(n, size=stale_count, replace=False).tolist())
    changed = history.groupby("sku_code")["unit_cost"].nunique()
    changed_skus = set(changed[changed > 1].index)

    headers, lines = [], []
    for i in range(n):
        supplier = suppliers.iloc[int(rng.integers(len(suppliers)))]
        own = products[products["primary_supplier_id"] == supplier["supplier_id"]]
        pool = own if len(own) else products
        po_date = start + timedelta(days=int(rng.integers(120, (end - start).days - 30)))
        invoice_no = f"INV-{i + 1:05d}"
        picks = list(rng.choice(pool["sku_code"].to_numpy(), size=min(int(rng.integers(1, 6)), len(pool)), replace=False))
        stale_line = None
        if i in stale_ids:
            candidates = [s for s in changed_skus
                          if s not in picks and previous_cost(history, s, po_date) is not None]
            if candidates:
                picks[0] = sorted(candidates)[int(rng.integers(len(candidates)))]
                stale_line = 0
        total = 0.0
        for line_no, sku in enumerate(picks, start=1):
            qty = int(rng.integers(1, 20)) * 12
            is_stale = stale_line == line_no - 1
            cost = previous_cost(history, sku, po_date) if is_stale else cost_on(history, sku, po_date)
            total += qty * cost
            lines.append({"invoice_number": invoice_no, "line_no": line_no, "sku_code": sku, "qty": qty,
                          "billed_unit_cost": round(cost, 2), "is_stale_cost": is_stale})
        headers.append({"invoice_number": invoice_no, "supplier_code": supplier["supplier_code"],
                        "supplier_name": supplier["name"], "po_number": f"PO-{int(rng.integers(1, 5000)):07d}",
                        "po_date": po_date, "invoice_date": po_date + timedelta(days=int(rng.integers(10, 40))),
                        "invoice_total": round(total, 2)})
    return pd.DataFrame(headers), pd.DataFrame(lines)


def draw_pdf(path, header, lines):
    # invariant=1 removes the timestamp and random ID reportlab adds,
    # so the same invoice always produces byte-identical PDFs
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    y = 740
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, y, header["supplier_name"])
    c.setFont("Helvetica", 10)
    c.drawString(60, y - 18, f"Supplier code: {header['supplier_code']}")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(550, y, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(550, y - 18, f"Invoice no: {header['invoice_number']}")
    c.drawRightString(550, y - 32, f"Invoice date: {header['invoice_date']}")
    c.drawRightString(550, y - 46, f"PO reference: {header['po_number']}")
    c.drawString(60, y - 60, "Bill to: Summit Trail Supply, Accounts Payable")

    y -= 100
    c.setFont("Helvetica-Bold", 10)
    for x, label in [(60, "Line"), (100, "SKU"), (260, "Qty"), (340, "Unit cost"), (450, "Amount")]:
        c.drawString(x, y, label)
    c.setFont("Helvetica", 10)
    for line in lines.itertuples():
        y -= 18
        c.drawString(60, y, str(line.line_no))
        c.drawString(100, y, line.sku_code)
        c.drawString(260, y, str(line.qty))
        c.drawString(340, y, f"${line.billed_unit_cost:,.2f}")
        c.drawString(450, y, f"${line.qty * line.billed_unit_cost:,.2f}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(340, y - 30, "Total due:")
    c.drawString(450, y - 30, f"${header['invoice_total']:,.2f}")
    c.save()


def generate_invoices(cfg):
    rng = make_rng(cfg, "invoices")
    out = cfg["paths"]["out_dir"]
    products, suppliers = read_master(cfg, "product"), read_master(cfg, "supplier")
    history = read_master(cfg, "product", all_extracts=True)[["sku_code", "unit_cost", "extract_date"]]
    headers, lines = build_invoices(products, history, suppliers, cfg, rng)

    pdf_dir = out / "docs" / "invoices"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for header in headers.to_dict("records"):
        draw_pdf(pdf_dir / f"{header['invoice_number']}.pdf", header,
                 lines[lines["invoice_number"] == header["invoice_number"]])
    return [write_csv(headers, out, "docs/invoice_headers/invoice_headers.csv"),
            write_csv(lines, out, "labels/invoice_line_labels.csv")]