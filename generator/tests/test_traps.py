from datetime import datetime, timezone

import numpy as np

from summit_gen import traps


def make_events(n):
    return [{"event_id": f"e{i}", "event_ts": "2026-05-11T08:00:00-07:00"} for i in range(n)]


def test_duplicate_share_is_close_to_the_rate():
    rng = np.random.default_rng(1)
    events = traps.inject_duplicates(make_events(20_000), rate=0.015, rng=rng)
    extra = len(events) - 20_000
    assert 0.01 < extra / 20_000 < 0.02


def test_duplicates_keep_the_same_event_id():
    rng = np.random.default_rng(2)
    events = traps.inject_duplicates(make_events(2_000), rate=0.05, rng=rng)
    ids = [e["event_id"] for e in events]
    assert len(set(ids)) == 2_000 and len(ids) > 2_000


def test_delay_never_changes_the_event_timestamp():
    rng = np.random.default_rng(3)
    events = traps.assign_delivery_delay(make_events(1_000), rate=0.5, max_hours=72, rng=rng)
    assert all(e["event_ts"] == "2026-05-11T08:00:00-07:00" for e in events)
    delays = [e["_delay_hours"] for e in events]
    assert max(delays) <= 72 and any(d > 0 for d in delays) and any(d == 0 for d in delays)


def test_impossible_sequence_puts_delivery_before_pickup():
    pickup = {"status": "PICKED_UP", "event_epoch_ms": 1_778_486_400_000}
    delivered = {"status": "DELIVERED", "event_epoch_ms": 0}
    traps.make_impossible_sequence(pickup, delivered)
    assert delivered["event_epoch_ms"] < pickup["event_epoch_ms"]


def test_strip_internal_removes_helper_fields():
    clean = traps.strip_internal({"event_id": "e1", "_delay_hours": 3.0, "_utc": datetime.now(timezone.utc)})
    assert clean == {"event_id": "e1"}