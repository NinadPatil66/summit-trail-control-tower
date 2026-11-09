"""Holiday and promotion calendars, written as dbt seed files."""
from datetime import date, timedelta

import pandas as pd

from .config import make_rng
from .master import read_master
from .writers import write_csv


def nth_weekday(year, month, weekday, n):
    """nth weekday of a month (weekday: Mon=0). n=-1 means the last one."""
    if n > 0:
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    nxt = date(year + month // 12, month % 12 + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def us_holidays(year):
    thanksgiving = nth_weekday(year, 11, 3, 4)
    return [
        (date(year, 1, 1), "New Year's Day", True),
        (nth_weekday(year, 1, 0, 3), "Martin Luther King Jr. Day", True),
        (nth_weekday(year, 2, 0, 3), "Presidents' Day", True),
        (nth_weekday(year, 5, 0, -1), "Memorial Day", True),
        (date(year, 6, 19), "Juneteenth", True),
        (date(year, 7, 4), "Independence Day", True),
        (nth_weekday(year, 9, 0, 1), "Labor Day", True),
        (nth_weekday(year, 10, 0, 2), "Columbus Day", True),
        (date(year, 11, 11), "Veterans Day", True),
        (thanksgiving, "Thanksgiving", True),
        (thanksgiving + timedelta(days=1), "Black Friday", False),
        (thanksgiving + timedelta(days=4), "Cyber Monday", False),
        (date(year, 12, 25), "Christmas Day", True),
    ]


def build_holidays(cfg):
    start, end = cfg["history"]["start"], cfg["history"]["end"]
    rows = [{"holiday_date": d, "holiday_name": name, "is_federal": fed,
             "is_peak_retail": name in ("Black Friday", "Cyber Monday", "Thanksgiving")}
            for year in range(start.year, end.year + 1)
            for d, name, fed in us_holidays(year) if start <= d <= end]
    return pd.DataFrame(rows).sort_values("holiday_date").reset_index(drop=True)


def build_promotions(sku_codes, cfg, rng):
    """Promo windows on a fixed set of SKUs. Thanksgiving week is always a promo week."""
    promo = cfg["planted"]["promo_spikes"]
    start, end = cfg["history"]["start"], cfg["history"]["end"]
    promo_skus = rng.choice(sku_codes, size=min(promo["skus"], len(sku_codes)), replace=False)

    first_monday = start + timedelta(days=(7 - start.weekday()) % 7)
    mondays = [first_monday + timedelta(weeks=w) for w in range((end - first_monday).days // 7)]
    must = [nth_weekday(y, 11, 3, 4) - timedelta(days=3) for y in range(start.year, end.year + 1)]
    must = [m for m in must if m in mondays]
    others = [m for m in mondays if all(abs((m - k).days) > 14 for k in must)]
    n_other = max(0, promo["windows"] - len(must))
    picked = sorted(must + list(rng.choice(others, size=n_other, replace=False)))

    rows = []
    for i, monday in enumerate(picked, start=1):
        subset = rng.choice(promo_skus, size=int(rng.integers(len(promo_skus) // 3, len(promo_skus) + 1)), replace=False)
        discount = int(rng.choice([10, 15, 20, 25]))
        for sku in sorted(subset):
            rows.append({"promo_id": f"PROMO-{i:03d}", "sku_code": sku,
                         "start_date": monday, "end_date": monday + timedelta(days=promo["window_days"] - 1),
                         "discount_pct": discount, "demand_multiplier": promo["multiplier"]})
    return pd.DataFrame(rows)


def generate_calendar(cfg):
    rng = make_rng(cfg, "calendar")
    seeds = cfg["paths"]["seeds_dir"]
    sku_codes = read_master(cfg, "product")["sku_code"].to_numpy()
    holidays = build_holidays(cfg)
    promos = build_promotions(sku_codes, cfg, rng)
    return [write_csv(holidays, seeds, "holidays.csv"), write_csv(promos, seeds, "promotions.csv")]