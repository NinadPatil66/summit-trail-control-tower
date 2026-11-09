"""Write files using the same folder layout the S3 stages will read."""
import json
from pathlib import Path


def _target(out_dir, rel_path):
    path = Path(out_dir) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(df, out_dir, rel_path):
    path = _target(out_dir, rel_path)
    # "\n" line endings so Windows and Mac produce identical files
    df.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
    return path


def write_ndjson(records, out_dir, rel_path, append=False):
    """One JSON object per line. append=True adds to an existing file."""
    path = _target(out_dir, rel_path)
    with open(path, "a" if append else "w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


def write_parquet(df, out_dir, rel_path):
    path = _target(out_dir, rel_path)
    df.to_parquet(path, index=False)
    return path


def dated_prefix(prefix, day):
    """erp/master + 2024-05-11 -> erp/master/dt=2024-05-11"""
    return f"{prefix}/dt={day:%Y-%m-%d}"


def event_prefix(prefix, ts):
    """wms/events + a timestamp -> wms/events/2026/05/11"""
    return f"{prefix}/{ts:%Y/%m/%d}"