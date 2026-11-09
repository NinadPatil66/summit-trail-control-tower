"""Quick checks on calendar, text, invoices and live output."""
import json
from datetime import datetime, timezone

import pandas as pd

from summit_gen.invoices import generate_invoices
from summit_gen.live import generate_live
from summit_gen.master import generate_master
from summit_gen.promo_calendar import generate_calendar
from summit_gen.text import generate_text


def test_calendar(small_cfg):
    generate_master(small_cfg)
    generate_calendar(small_cfg)
    seeds = small_cfg["paths"]["seeds_dir"]
    holidays = pd.read_csv(seeds / "holidays.csv")
    promos = pd.read_csv(seeds / "promotions.csv")
    assert "Black Friday" in set(holidays["holiday_name"])
    assert promos["promo_id"].nunique() == small_cfg["planted"]["promo_spikes"]["windows"]
    assert promos["sku_code"].nunique() <= small_cfg["planted"]["promo_spikes"]["skus"]


def test_text_has_one_label_per_message(small_cfg):
    generate_master(small_cfg)
    generate_text(small_cfg)
    out = small_cfg["paths"]["out_dir"]
    for name, label in [("supplier_emails", "supplier_email_labels"), ("carrier_notes", "carrier_note_labels"),
                        ("return_comments", "return_comment_labels")]:
        messages = (out / "docs" / "text" / f"{name}.ndjson").read_text(encoding="utf-8").splitlines()
        labels = pd.read_csv(out / "labels" / f"{label}.csv")
        assert len(messages) == len(labels) > 0


def test_invoices_have_pdfs_and_stale_lines(small_cfg):
    generate_master(small_cfg)
    generate_invoices(small_cfg)
    out = small_cfg["paths"]["out_dir"]
    assert len(list((out / "docs" / "invoices").glob("*.pdf"))) == small_cfg["invoices"]["count"]
    lines = pd.read_csv(out / "labels" / "invoice_line_labels.csv")
    assert lines["is_stale_cost"].sum() >= 1


def test_live_writes_wms_and_tms_files(small_cfg):
    generate_master(small_cfg)
    written = generate_live(small_cfg, datetime(2026, 5, 11, 15, 0, tzinfo=timezone.utc), windows=2)
    wms = [p for p in written if p.name.startswith("wms_")]
    assert wms and any(p.name.startswith("tms_") for p in written)
    first = json.loads(wms[0].read_text(encoding="utf-8").splitlines()[0])
    assert "lot_number" in first and "handling_unit" in first     # past the schema drift month
    assert not any(key.startswith("_") for key in first)