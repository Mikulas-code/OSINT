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

import sys
from datetime import date

import pandas as pd

from common import DATA_RAW, PERIOD_END, PERIOD_START, spacetrack_query

# One query: payloads (not rocket bodies or debris) of US and CIS (= Russia)
# launched in the study period. Decayed satellites are kept on purpose.
QUERY = (
    "/basicspacedata/query/class/satcat"
    f"/LAUNCH/{PERIOD_START}--{PERIOD_END}"
    "/OBJECT_TYPE/PAYLOAD"
    "/COUNTRY/US,CIS"
    "/orderby/LAUNCH asc"
    "/format/csv"
)

# Satellites deployed from the ISS get the ISS designator (1998-067xx) and the
# ISS launch date (1998-11-20), so the query above misses them. We download all
# of them; 02_classify.py picks those that reached the ISS in the study period.
ISS_QUERY = (
    "/basicspacedata/query/class/satcat"
    "/INTLDES/~~1998-067"
    "/OBJECT_TYPE/PAYLOAD"
    "/COUNTRY/US,CIS"
    "/orderby/NORAD_CAT_ID asc"
    "/format/csv"
)

# Columns the later steps rely on (see ANALYSIS_PLAN.md, step 1)
EXPECTED_COLUMNS = [
    "NORAD_CAT_ID", "OBJECT_NAME", "INTLDES", "COUNTRY", "LAUNCH", "SITE",
    "DECAY", "PERIOD", "INCLINATION", "APOGEE", "PERIGEE",
]


def main():
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    out_file = DATA_RAW / f"satcat_{date.today().isoformat()}.csv"

    if out_file.exists():
        print(f"{out_file.name} already exists - skipping download.")
    else:
        out_file.write_text(spacetrack_query(QUERY), encoding="utf-8")
        print(f"Saved to {out_file}")

    iss_file = DATA_RAW / f"iss_deployed_{date.today().isoformat()}.csv"
    if iss_file.exists():
        print(f"{iss_file.name} already exists - skipping download.")
    else:
        iss_file.write_text(spacetrack_query(ISS_QUERY), encoding="utf-8")
        print(f"Saved to {iss_file}")
    print(f"ISS-deployed payloads (all years): {len(pd.read_csv(iss_file))}")

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
