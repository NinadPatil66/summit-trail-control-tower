"""Master data: DCs, carriers, suppliers, SKUs (from M5), customers, kits, SKU crosswalk.

Writes one full extract per quarter to data/generated/erp/master/dt=YYYY-MM-DD/.
Unit costs and supplier tiers change between extracts, so dbt snapshots have
real history to record.
"""
import re
from datetime import timedelta

import numpy as np
import pandas as pd
from faker import Faker

from .config import make_rng
from .writers import dated_prefix, write_csv

CATEGORY = {"HOBBIES": "Outdoor gear", "HOUSEHOLD": "Home goods", "FOODS": "Trail consumables"}
DEPT_PREFIX = {"HOBBIES": "OUTDOOR", "HOUSEHOLD": "HOME", "FOODS": "TRAIL"}
NAME_WORDS = {
    "Outdoor gear": (["Trail", "Summit", "Ridge", "Canyon", "Alpine", "Basecamp"],
                     ["Tent", "Backpack", "Headlamp", "Trekking Pole", "Sleeping Bag", "Camp Stove", "Water Filter", "Hammock"]),
    "Home goods": (["Cedar", "Harbor", "Meadow", "Stone", "Maple", "Linen"],
                   ["Storage Bin", "Lantern", "Throw Blanket", "Cookware Set", "Shelf", "Doormat", "Towel Set", "Candle"]),
    "Trail consumables": (["Peak", "Trailhead", "Campfire", "Switchback", "Ranger", "Sunrise"],
                          ["Energy Bar", "Trail Mix", "Freeze-Dried Meal", "Electrolyte Mix", "Jerky", "Coffee Pouch", "Oatmeal Cup", "Granola"]),
}
# country: (share of suppliers, promised lead time range in days)
COUNTRIES = {"US": (0.45, (7, 14)), "MX": (0.15, (10, 18)), "CA": (0.10, (7, 12)),
             "CN": (0.15, (35, 50)), "VN": (0.10, (35, 50)), "IN": (0.05, (30, 45))}
CARRIERS = [("CR-1", "Redline Freight", "LTL"), ("CR-2", "Northstar Parcel", "PARCEL"),
            ("CR-3", "Bayou Express", "LTL"), ("CR-4", "Keystone Logistics", "FTL"),
            ("CR-5", "Cascade Courier", "PARCEL")]


# ---------- M5 input ----------
def m5_day_columns(cfg):
    return [f"d_{i}" for i in range(cfg["m5"]["first_day"], cfg["m5"]["last_day"] + 1)]


def load_m5_items(cfg):
    """Total units per M5 item over the 730 days we use, plus its median price."""
    m5_dir = cfg["paths"]["m5_dir"]
    sales_path, prices_path = m5_dir / "sales_train_evaluation.csv", m5_dir / "sell_prices.csv"
    for p in (sales_path, prices_path):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found. Download the M5 files first (Step 3).")
    days = m5_day_columns(cfg)
    sales = pd.read_csv(sales_path, usecols=["item_id", "dept_id", "cat_id", *days],
                        dtype={d: "int32" for d in days})
    totals = sales[["item_id", "dept_id", "cat_id"]].assign(total_units=sales[days].sum(axis=1))
    items = totals.groupby(["item_id", "dept_id", "cat_id"], as_index=False)["total_units"].sum()
    prices = pd.read_csv(prices_path, usecols=["item_id", "sell_price"])
    median_price = prices.groupby("item_id", as_index=False)["sell_price"].median()
    return items.merge(median_price, on="item_id", how="left")


# ---------- builders ----------
def build_dcs(cfg):
    cols = ["dc_id", "dc_code", "city", "state", "zip", "timezone"]
    return pd.DataFrame([{c: d[c] for c in cols} for d in cfg["dcs"]])


def build_carriers():
    return pd.DataFrame([{"carrier_id": i + 1, "carrier_code": c, "name": n, "mode": m}
                         for i, (c, n, m) in enumerate(CARRIERS)])


def build_suppliers(cfg, rng, fake):
    n = cfg["entities"]["suppliers"]
    countries = list(COUNTRIES)
    shares = np.array([COUNTRIES[c][0] for c in countries])
    rows = []
    for i in range(n):
        name = fake.company()
        country = rng.choice(countries, p=shares / shares.sum())
        lo, hi = COUNTRIES[country][1]
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())[:20]
        rows.append({
            "supplier_id": i + 1,
            "supplier_code": f"SUP-{i + 1:03d}",
            "name": name,
            "country": country,
            "tier": rng.choice(["A", "B", "C"], p=[0.2, 0.5, 0.3]),
            "promised_lead_time_days": int(rng.integers(lo, hi + 1)),
            "payment_terms": rng.choice(["NET30", "NET45", "NET60"]),
            "contact_email": f"orders@{slug}.example",
            "contact_phone": fake.phone_number(),
        })
    return pd.DataFrame(rows)


def build_products(items, suppliers, cfg, rng):
    n = cfg["entities"]["skus"]
    top = (items.sort_values(["total_units", "item_id"], ascending=[False, True])
                .head(n).reset_index(drop=True))
    n = len(top)
    cat_key = top["cat_id"].astype(str)
    category = cat_key.map(CATEGORY)
    department = [DEPT_PREFIX[c] + d[len(c):] for c, d in zip(cat_key, top["dept_id"])]
    names = []
    for cat in category:
        adjectives, nouns = NAME_WORDS[cat]
        names.append(f"{rng.choice(adjectives)} {rng.choice(nouns)} {int(rng.integers(100, 1000))}")
    list_price = top["sell_price"].fillna(5.0).round(2)
    unit_cost = (list_price * rng.uniform(0.45, 0.70, n)).round(2)

    # Every supplier gets at least one SKU; the rest follow a skewed split,
    # with the planted supplier boosted so its drift hits plenty of SKUs.
    supplier_ids = suppliers["supplier_id"].to_numpy()
    weights = 1 / np.arange(1, len(supplier_ids) + 1) ** 0.8
    planted = cfg["planted"]["supplier_lead_time_drift"]["supplier"]
    weights[suppliers["supplier_code"].to_numpy() == planted] *= 3
    assigned = rng.choice(supplier_ids, size=n, p=weights / weights.sum())
    first = rng.permutation(n)[: len(supplier_ids)]
    assigned[first] = supplier_ids[: len(first)]

    return pd.DataFrame({
        "sku_id": np.arange(1, n + 1),
        "sku_code": [f"SKU-{i:05d}" for i in range(1, n + 1)],
        "m5_item_id": top["item_id"],
        "name": names,
        "category": category,
        "department": department,
        "eaches_per_case": rng.choice([6, 12, 24, 48], size=n),
        "unit_cost": unit_cost,
        "list_price": list_price,
        "primary_supplier_id": assigned,
    })


def build_customers(cfg, rng, fake):
    start = cfg["history"]["start"]
    span = (cfg["history"]["end"] - start).days
    dcs = cfg["dcs"]
    rows = []
    for i in range(cfg["entities"]["customers"]):
        dc = dcs[int(rng.integers(len(dcs)))]
        # about 85% exist before history starts; the rest join later (orphan-key trap)
        offset = int(rng.integers(-730, 0)) if rng.random() < 0.85 else int(rng.integers(0, span))
        rows.append({
            "customer_id": i + 1,
            "name": fake.company(),
            "customer_type": rng.choice(["RETAIL", "B2B"], p=[0.7, 0.3]),
            "home_dc_id": dc["dc_id"],
            "zip": fake.zipcode_in_state(dc["state"]),
            "created_at": start + timedelta(days=offset),
        })
    return pd.DataFrame(rows)


def build_kits(products, cfg, rng):
    """Kits are SKUs made of other SKUs. About 10% include another kit (two levels)."""
    n_kits = min(cfg["entities"]["kits"], len(products) // 4)
    outdoor = products.loc[products["category"] == "Outdoor gear", "sku_id"].to_numpy()
    pool = outdoor if len(outdoor) >= n_kits else products["sku_id"].to_numpy()
    kits = rng.choice(pool, size=n_kits, replace=False)
    components = np.setdiff1d(products["sku_id"].to_numpy(), kits)
    rows = []
    for i, kit in enumerate(kits):
        parts = list(rng.choice(components, size=int(rng.integers(3, 7)), replace=False))
        if i > 0 and rng.random() < 0.10:
            parts[0] = kits[int(rng.integers(0, i))]   # an earlier kit, so no cycles
        for part in parts:
            rows.append({"kit_sku_id": int(kit), "component_sku_id": int(part),
                         "qty_per_kit": int(rng.integers(1, 5))})
    return pd.DataFrame(rows)


def build_crosswalk(products, cfg, rng):
    start = cfg["history"]["start"]
    span = (cfg["history"]["end"] - start).days
    n = cfg["entities"]["crosswalk_merges"]
    new_codes = rng.choice(products["sku_code"].to_numpy(), size=n, replace=False)
    return pd.DataFrame({
        "old_sku_code": [f"SKU-9{i:04d}" for i in range(1, n + 1)],
        "new_sku_code": new_codes,
        "effective_date": [start + timedelta(days=int(d)) for d in rng.integers(30, span, n)],
    })


# ---------- quarterly changes ----------
def extract_dates(cfg):
    start, end = cfg["history"]["start"], cfg["history"]["end"]
    step = cfg["master_changes"]["extract_every_days"]
    days = range(0, (end - start).days + 1, step)
    return [start + timedelta(days=d) for d in days]


def apply_quarter_changes(products, suppliers, day, cfg, rng):
    mc = cfg["master_changes"]
    products, suppliers = products.copy(), suppliers.copy()
    changed = rng.random(len(products)) < mc["pct_skus_cost_change"]
    lo, hi = mc["cost_change_pct"]
    bump = 1 + rng.uniform(lo, hi, changed.sum()) / 100
    products.loc[changed, "unit_cost"] = (products.loc[changed, "unit_cost"] * bump).round(2)
    products.loc[changed, "updated_at"] = day
    moved = rng.random(len(suppliers)) < mc["pct_suppliers_tier_change"]
    suppliers.loc[moved, "tier"] = rng.choice(["A", "B", "C"], size=moved.sum())
    suppliers.loc[moved, "updated_at"] = day
    return products, suppliers


# ---------- entry point ----------
def generate_master(cfg, items=None):
    """Build everything and write one extract folder per quarter. Returns the folder paths."""
    rng = make_rng(cfg, "master")
    fake = Faker("en_US")
    fake.seed_instance(cfg["seed"])
    items = load_m5_items(cfg) if items is None else items
    start = cfg["history"]["start"]

    dcs, carriers = build_dcs(cfg), build_carriers()
    suppliers = build_suppliers(cfg, rng, fake)
    products = build_products(items, suppliers, cfg, rng)
    customers = build_customers(cfg, rng, fake)
    kits = build_kits(products, cfg, rng)
    crosswalk = build_crosswalk(products, cfg, rng)
    products["updated_at"], suppliers["updated_at"] = start, start

    folders = []
    for q, day in enumerate(extract_dates(cfg)):
        if q > 0:
            products, suppliers = apply_quarter_changes(products, suppliers, day, cfg, rng)
        prefix = dated_prefix("erp/master", day)
        out = cfg["paths"]["out_dir"]
        write_csv(dcs, out, f"{prefix}/dc.csv")
        write_csv(carriers, out, f"{prefix}/carrier.csv")
        write_csv(suppliers, out, f"{prefix}/supplier.csv")
        write_csv(products, out, f"{prefix}/product.csv")
        write_csv(customers[customers["created_at"] <= day], out, f"{prefix}/customer.csv")
        write_csv(kits, out, f"{prefix}/kit_bom.csv")
        write_csv(crosswalk, out, f"{prefix}/sku_crosswalk.csv")
        folders.append(out / prefix)
    return folders


def read_master(cfg, name, all_extracts=False):
    """Read a master file back. Latest extract, or every extract with its date."""
    base = cfg["paths"]["out_dir"] / "erp" / "master"
    folders = sorted(base.glob("dt=*"))
    if not folders:
        raise FileNotFoundError(f"No master extracts in {base}. Run: python -m summit_gen.cli master")
    if not all_extracts:
        return pd.read_csv(folders[-1] / f"{name}.csv")
    frames = [pd.read_csv(f / f"{name}.csv").assign(extract_date=f.name[3:]) for f in folders]
    return pd.concat(frames, ignore_index=True)