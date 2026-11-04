"""Shared settings used by all analysis scripts (paths, study period)."""

from pathlib import Path

# Project root = parent folder of src/
ROOT = Path(__file__).resolve().parent.parent

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "output" / "figures"
TABLES = ROOT / "output" / "tables"
MANUAL_OVERRIDES = ROOT / "manual_overrides.csv"

# Study period for RQ1/RQ2 (inclusive)
PERIOD_START = "2022-02-24"  # start of the Russian invasion of Ukraine
PERIOD_END = "2026-09-30"


def newest_file(folder, pattern):
    """Return the newest file matching pattern (file names contain the date)."""
    files = sorted(folder.glob(pattern))
    if not files:
        raise SystemExit(f"No file {pattern} in {folder}")
    return files[-1]
