"""Shared settings and helpers used by all analysis scripts."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

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

SPACETRACK_URL = "https://www.space-track.org"


def newest_file(folder, pattern):
    """Return the newest file matching pattern (file names contain the date)."""
    files = sorted(folder.glob(pattern))
    if not files:
        raise SystemExit(f"No file {pattern} in {folder}")
    return files[-1]


def spacetrack_query(query):
    """Log in to Space-Track, run one query and return the response text.

    query = the part after the base URL, e.g. '/basicspacedata/query/class/satcat/...'
    Each call = login + 1 query + logout, well within the API rate limits
    (30 requests/minute, 300/hour).
    """
    load_dotenv(ROOT / ".env")
    user = os.getenv("SPACETRACK_USER")
    password = os.getenv("SPACETRACK_PASS")
    if not user or not password:
        sys.exit("Missing SPACETRACK_USER or SPACETRACK_PASS in .env")

    # A Session keeps the login cookie for the following requests
    with requests.Session() as session:
        resp = session.post(SPACETRACK_URL + "/ajaxauth/login",
                            data={"identity": user, "password": password})
        resp.raise_for_status()
        # Space-Track returns HTTP 200 even for a wrong password,
        # the failure is only in the response body.
        if "Failed" in resp.text:
            sys.exit("Login to Space-Track failed - check credentials in .env")
        print("Logged in to Space-Track.")

        print("Query:", SPACETRACK_URL + query)
        resp = session.get(SPACETRACK_URL + query, timeout=120)
        resp.raise_for_status()

        session.get(SPACETRACK_URL + "/ajaxauth/logout")
        return resp.text
