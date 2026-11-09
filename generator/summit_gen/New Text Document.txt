"""Command line: python -m summit_gen.cli <command>

Run from the generator/ folder:
  python -m summit_gen.cli master      # quarterly master extracts
  python -m summit_gen.cli calendar    # holidays.csv and promotions.csv into dbt/seeds
  python -m summit_gen.cli text        # emails, carrier notes, return comments + labels
  python -m summit_gen.cli invoices    # PDF invoices + labels
  python -m summit_gen.cli all         # the four above, in order
  python -m summit_gen.cli live --start 2026-05-11T08:00 --windows 12
"""
import argparse
import time

from .config import load_config
from .invoices import generate_invoices
from .live import generate_live, parse_start
from .master import generate_master
from .promo_calendar import generate_calendar
from .text import generate_text

STEPS = {"master": generate_master, "calendar": generate_calendar,
         "text": generate_text, "invoices": generate_invoices}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="summit_gen")
    parser.add_argument("command", choices=[*STEPS, "all", "live"])
    parser.add_argument("--config", help="path to a different config.yaml")
    parser.add_argument("--start", help="live only: first window, UTC, e.g. 2026-05-11T08:00")
    parser.add_argument("--windows", type=int, default=1, help="live only: number of 5-minute windows")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    names = list(STEPS) if args.command == "all" else [args.command]
    for name in names:
        began = time.perf_counter()
        if name == "live":
            written = generate_live(cfg, parse_start(args.start), args.windows)
        else:
            written = STEPS[name](cfg)
        print(f"{name}: wrote {len(written)} file(s) or folder(s) in {time.perf_counter() - began:.1f}s")


if __name__ == "__main__":
    main()