"""Live event files: one WMS file and one TMS file per 5-minute window.

Used for the Snowpipe module and the daily simulation. Late events keep their
real timestamp but are written into a later window's file, like a real feed.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import traps
from .config import make_rng
from .master import read_master
from .writers import event_prefix, write_ndjson

WINDOW = timedelta(minutes=5)
WMS_TYPES = {"RECEIPT": 0.08, "PUTAWAY": 0.08, "PICK": 0.40, "PACK": 0.30,
             "TRANSFER": 0.04, "ADJUST": 0.05, "CYCLE_COUNT": 0.05}
FACILITIES = ["MEM", "ATL", "DFW", "SDF", "CMH", "RNO", "ONT", "ABE"]


def window_start(ts):
    """Round a UTC time down to its 5-minute window."""
    return ts.replace(minute=ts.minute - ts.minute % 5, second=0, microsecond=0)


def shift_name(local_hour):
    return "DAY" if 6 <= local_hour < 14 else "SWING" if 14 <= local_hour < 22 else "NIGHT"


def build_wms_events(win, dcs, skus, cfg, rng):
    drift_from = cfg["history"]["start"] + timedelta(days=30 * cfg["traps"]["schema_drift_month"])
    types, weights = list(WMS_TYPES), list(WMS_TYPES.values())
    tag = int(win.timestamp() // 60)
    events = []
    for i in range(cfg["live"]["wms_events_per_file"]):
        dc = dcs[int(rng.integers(len(dcs)))]
        utc = win + timedelta(seconds=int(rng.integers(0, 300)))
        local = utc.astimezone(ZoneInfo(dc["timezone"]))
        kind = types[int(rng.choice(len(types), p=weights))]
        event = {"event_id": f"wms-{tag}-{i:04d}", "event_type": kind,
                 "event_ts": local.isoformat(timespec="seconds"), "dc_code": dc["dc_code"],
                 "sku_code": str(skus[int(rng.integers(len(skus)))]), "qty": int(rng.integers(1, 49)), "uom": "EA",
                 "order_line_id": int(rng.integers(1, 20_000_000)) if kind in ("PICK", "PACK") else None,
                 "location": {"zone": str(rng.choice(list("ABCDEF"))), "aisle": f"{int(rng.integers(1, 40)):02d}",
                              "bin": f"{int(rng.integers(1, 20)):02d}"},
                 "operator_id": f"OP-{int(rng.integers(100, 400))}", "shift": shift_name(local.hour),
                 "_utc": utc}
        if utc.date() >= drift_from:
            traps.add_schema_drift(event, rng)
        events.append(event)
    return events


def build_tms_events(win, carriers, cfg, rng):
    tag = int(win.timestamp() // 60)
    rate = cfg["traps"]["impossible_sequence_rate"]
    events = []
    for i in range(cfg["live"]["tms_events_per_file"]):
        carrier = str(carriers[int(rng.integers(len(carriers)))])
        utc = win + timedelta(seconds=int(rng.integers(0, 300)))
        ms = int(utc.timestamp() * 1000)
        status = str(rng.choice(["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "EXCEPTION"],
                                p=[0.15, 0.40, 0.15, 0.22, 0.08]))
        scans = [{"facility": str(rng.choice(FACILITIES)), "scan_epoch_ms": ms - int(rng.integers(0, 6)) * 3_600_000,
                  "code": str(rng.choice(["AR", "DP", "OD"]))} for _ in range(int(rng.integers(1, 4)))]
        event = {"shipment_id": f"SHP-{int(rng.integers(1, 2_000_000)):07d}",
                 "tracking_number": f"{carrier.replace('-', '')}-{int(rng.integers(10**7, 10**8))}",
                 "carrier_code": carrier, "event_epoch_ms": ms, "status": status, "scans": scans,
                 "note": None, "_utc": utc}
        events.append(event)
        if status == "PICKED_UP" and rng.random() < rate:
            delivered = {**event, "status": "DELIVERED", "scans": []}
            traps.make_impossible_sequence(event, delivered)
            events.append(delivered)
    return events


def write_window_files(events, prefix, name, cfg):
    """Group events by the window they land in (after any delay) and append them."""
    by_file = {}
    for e in events:
        landed = window_start(traps.delivery_time(e, e["_utc"]))
        rel = f"{event_prefix(prefix, landed)}/{name}_{landed:%Y%m%d_%H%M}.{'ndjson' if name == 'wms' else 'json'}"
        by_file.setdefault(rel, []).append(traps.strip_internal(e))
    return [write_ndjson(rows, cfg["paths"]["out_dir"], rel, append=True) for rel, rows in sorted(by_file.items())]


def generate_live(cfg, start, windows=1):
    """Write `windows` consecutive 5-minute windows starting at `start` (UTC)."""
    dcs = cfg["dcs"]
    skus = read_master(cfg, "product")["sku_code"].to_numpy()
    carriers = read_master(cfg, "carrier")["carrier_code"].to_numpy()
    t = cfg["traps"]
    win = window_start(start.astimezone(timezone.utc))
    written = set()
    for _ in range(windows):
        rng = make_rng(cfg, "live", int(win.timestamp()))
        wms = build_wms_events(win, dcs, skus, cfg, rng)
        tms = build_tms_events(win, carriers, cfg, rng)
        for events, prefix, name in ((wms, "wms/events", "wms"), (tms, "tms/events", "tms")):
            events = traps.inject_duplicates(events, t["duplicate_rate"], rng)
            events = traps.assign_delivery_delay(events, t["late_event_rate"], t["late_event_max_hours"], rng)
            written.update(write_window_files(events, prefix, name, cfg))
        win += WINDOW
    return sorted(written)


def parse_start(text):
    """'2026-05-11T08:00' (read as UTC) or None for the current time."""
    if not text:
        return datetime.now(timezone.utc)
    ts = datetime.fromisoformat(text)
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)