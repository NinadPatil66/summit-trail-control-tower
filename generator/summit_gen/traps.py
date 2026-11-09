"""Data quality traps. Each one is a small function you can test on its own.

Events are dicts. Every function takes the rng it should draw from, so the
same seed always plants the same traps.
"""
import copy
from datetime import timedelta


def inject_duplicates(events, rate, rng):
    """Re-send a share of events unchanged (same event_id), like a retrying source."""
    return events + [copy.deepcopy(e) for e in events if rng.random() < rate]


def assign_delivery_delay(events, rate, max_hours, rng):
    """Mark some events to arrive late. Their own timestamp never changes."""
    for e in events:
        e["_delay_hours"] = float(rng.uniform(1, max_hours)) if rng.random() < rate else 0.0
    return events


def delivery_time(event, event_time):
    """When the event lands in a file: when it happened, plus any delay."""
    return event_time + timedelta(hours=event.get("_delay_hours", 0.0))


def add_schema_drift(event, rng):
    """From the drift month on, WMS events carry two new fields."""
    event["lot_number"] = f"L{int(rng.integers(2400, 2700))}-{int(rng.integers(10, 99))}"
    event["handling_unit"] = {"type": str(rng.choice(["PALLET", "CASE", "TOTE"])),
                              "hu_id": f"HU-{int(rng.integers(10000, 99999))}"}
    return event


def make_impossible_sequence(pickup, delivered, minutes_before=90):
    """Make DELIVERED happen before PICKED_UP for one shipment (a broken feed)."""
    delivered["event_epoch_ms"] = pickup["event_epoch_ms"] - minutes_before * 60_000
    return pickup, delivered


def strip_internal(event):
    """Remove helper fields (names starting with _) before writing."""
    return {k: v for k, v in event.items() if not k.startswith("_")}