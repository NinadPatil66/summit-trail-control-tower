"""Load config.yaml and hand out seeded random number generators."""
from pathlib import Path

import numpy as np
import yaml

GEN_DIR = Path(__file__).resolve().parents[1]   # .../generator
REPO_ROOT = GEN_DIR.parent                      # the repo root

# Each module draws from its own random stream. Changing one module
# never shifts the random numbers another module gets.
STREAMS = {"master": 1, "calendar": 2, "text": 3, "invoices": 4, "live": 5, "traps": 6}


def load_config(path=None, overrides=None):
    """Read config.yaml, apply optional overrides, turn paths into full paths."""
    path = Path(path) if path else GEN_DIR / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if overrides:
        _merge(cfg, overrides)
    for key, value in cfg["paths"].items():
        p = Path(value)
        cfg["paths"][key] = p if p.is_absolute() else REPO_ROOT / p
    return cfg


def _merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def make_rng(cfg, stream, *extra):
    """A seeded generator: same seed + same stream = same numbers, every run."""
    return np.random.default_rng([cfg["seed"], STREAMS[stream], *extra])