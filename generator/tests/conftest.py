"""Shared test setup: a tiny fake M5 file and a small config that writes to a temp folder."""
import numpy as np
import pandas as pd
import pytest

from summit_gen.config import load_config

STORES = ["CA_1", "CA_2", "CA_3", "CA_4", "TX_1", "TX_2", "TX_3", "WI_1", "WI_2", "WI_3"]


def write_fake_m5(folder, items_per_cat=20, first_day=1212, last_day=1941):
    """Same columns as the real M5 files, far fewer rows."""
    rng = np.random.default_rng(0)
    days = [f"d_{i}" for i in range(first_day, last_day + 1)]
    rows, prices = [], []
    for cat, depts in {"HOBBIES": 2, "HOUSEHOLD": 2, "FOODS": 3}.items():
        for n in range(items_per_cat):
            dept = f"{cat}_{n % depts + 1}"
            item = f"{dept}_{n:03d}"
            for store in STORES:
                rows.append({"id": f"{item}_{store}_evaluation", "item_id": item, "dept_id": dept,
                             "cat_id": cat, "store_id": store, "state_id": store[:2],
                             **dict(zip(days, rng.poisson(rng.uniform(0.2, 6), len(days))))})
                prices.append({"store_id": store, "item_id": item, "wm_yr_wk": 11101,
                               "sell_price": round(float(rng.uniform(1, 40)), 2)})
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / "sales_train_evaluation.csv", index=False)
    pd.DataFrame(prices).to_csv(folder / "sell_prices.csv", index=False)


SMALL = {
    "entities": {"suppliers": 20, "skus": 50, "customers": 30, "kits": 6, "crosswalk_merges": 5},
    "text": {"supplier_emails": 40, "carrier_notes": 80, "return_comments": 40},
    "invoices": {"count": 12},
    "live": {"wms_events_per_file": 40, "tms_events_per_file": 20},
    "planted": {"promo_spikes": {"skus": 8, "windows": 4}},
}


@pytest.fixture(scope="session")
def fake_m5_dir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("m5")
    write_fake_m5(folder)
    return folder


@pytest.fixture
def small_cfg(tmp_path, fake_m5_dir):
    """A small config whose output goes to a fresh temp folder for each test."""
    paths = {"m5_dir": str(fake_m5_dir), "out_dir": str(tmp_path / "generated"),
             "seeds_dir": str(tmp_path / "seeds")}
    return load_config(overrides={**SMALL, "paths": paths})