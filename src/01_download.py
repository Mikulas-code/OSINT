"""Step 1 - download SATCAT data for US and Russian payloads from Space-Track.

What it does:
  1. Logs in to Space-Track with credentials from .env
  2. Downloads one CSV with all payloads launched by US and CIS (Russia)
     in the study period (including satellites that have already decayed)
  3. Saves it to data/raw/satcat_YYYY-MM-DD.csv (date = download date)
  4. Prints the columns and record counts so we can check the data

The data is downloaded only once per day: if today's file already exists,
the script does not contact Space-Track again.

Usage (from project root):  python src/01_download.py
"""

import io
import os
import sys
from datetime import date

import pandas as pd
import requests
from dotenv import load_dotenv

from common import DATA_RAW, PERIOD_END, PERIOD_START

BASE_URL = "https://www.space-track.org"
LOGIN_URL = BASE_URL + "/ajaxauth/login"
LOGOUT_URL = BASE_URL + "/ajaxauth/logout"

# One query: payloads (not rocket bodies or debris) of US and CIS (= Russia)
# launched in the study period. Decayed satellites are kept on purpose.
QUERY_URL = (
    BASE_URL
    + "/basicspacedata/query/class/satcat"
    + f"/LAUNCH/{PERIOD_START}--{PERIOD_END}"
    + "/OBJECT_TYPE/PAYLOAD"
    + "/COUNTRY/US,CIS"
    + "/orderby/LAUNCH asc"
    + "/format/csv"
)

# Columns the later steps rely on (see ANALYSIS_PLAN.md, step 1)
EXPECTED_COLUMNS = [
    "NORAD_CAT_ID", "OBJECT_NAME", "INTLDES", "COUNTRY", "LAUNCH", "SITE",
    "DECAY", "PERIOD", "INCLINATION", "APOGEE", "PERIGEE",
]


def download_satcat() -> str:
    """Log in, run the query and return the CSV text."""
    load_dotenv()
    user = os.getenv("SPACETRACK_USER")
    password = os.getenv("SPACETRACK_PASS")
    if not user or not password:
        sys.exit("Missing SPACETRACK_USER or SPACETRACK_PASS in .env")

    # A Session keeps the login cookie for the following requests
    with requests.Session() as session:
        resp = session.post(LOGIN_URL, data={"identity": user, "password": password})
        resp.raise_for_status()
        # Space-Track returns HTTP 200 even for a wrong password,
        # the failure is only in the response body.
        if "Failed" in resp.text:
            sys.exit("Login to Space-Track failed - check credentials in .env")
        print("Logged in to Space-Track.")

        print("Query:", QUERY_URL)
        resp = session.get(QUERY_URL, timeout=120)
        resp.raise_for_status()

        session.get(LOGOUT_URL)
        return resp.text


def main():
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    out_file = DATA_RAW / f"satcat_{date.today().isoformat()}.csv"

    if out_file.exists():
        print(f"{out_file.name} already exists - skipping download.")
    else:
        csv_text = download_satcat()
        out_file.write_text(csv_text, encoding="utf-8")
        print(f"Saved to {out_file}")

    # --- Quick check of what we downloaded ---
    df = pd.read_csv(out_file)
    print(f"\nRecords downloaded: {len(df)}")
    print("Columns:", list(df.columns))

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print("\nWARNING - expected columns are missing:", missing)
        print(df.head().to_string())
        sys.exit(1)

    print("\nRecords by country:")
    print(df["COUNTRY"].value_counts().to_string())
    print("\nAlready decayed (DECAY filled):", df["DECAY"].notna().sum())
    print(f"Launch dates from {df['LAUNCH'].min()} to {df['LAUNCH'].max()}")
    print("\nSample rows:")
    print(df[EXPECTED_COLUMNS].sample(5, random_state=1).to_string(index=False))


if __name__ == "__main__":
    main()
