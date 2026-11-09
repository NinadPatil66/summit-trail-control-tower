"""Same seed in, byte-identical files out."""
import hashlib
from datetime import datetime, timezone

from summit_gen.config import load_config
from summit_gen.invoices import generate_invoices
from summit_gen.live import generate_live
from summit_gen.master import generate_master
from summit_gen.promo_calendar import generate_calendar
from summit_gen.text import generate_text

from conftest import SMALL


def run_everything(base, m5_dir):
    paths = {"m5_dir": str(m5_dir), "out_dir": str(base / "generated"), "seeds_dir": str(base / "seeds")}
    cfg = load_config(overrides={**SMALL, "paths": paths})
    generate_master(cfg)
    generate_calendar(cfg)
    generate_text(cfg)
    generate_invoices(cfg)
    generate_live(cfg, datetime(2026, 5, 11, 15, 0, tzinfo=timezone.utc), windows=3)
    return base


def file_hashes(base):
    return {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob("*")) if p.is_file()}


def test_two_runs_produce_identical_files(tmp_path, fake_m5_dir):
    first = file_hashes(run_everything(tmp_path / "run1", fake_m5_dir))
    second = file_hashes(run_everything(tmp_path / "run2", fake_m5_dir))
    assert len(first) > 20
    assert first == second