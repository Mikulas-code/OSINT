"""Step 4 (optional, RQ3) - Kosmos 1408 debris on orbit over time.

Russia destroyed its own satellite Kosmos 1408 with an anti-satellite (ASAT)
missile on 15 Nov 2021. Debris pieces keep the international designator of
the original satellite (1982-092), so one SATCAT query finds them all.

What it does:
  1. Downloads all objects with designator 1982-092 (satellite + debris)
     to data/raw/kosmos1408_YYYY-MM-DD.csv (once per day)
  2. Checks that the parent satellite is really Kosmos 1408
  3. For every month from 11/2021 counts debris still on orbit
     (DECAY empty or later than the end of the month)
  4. Saves output/tables/rq3_debris.csv and output/figures/fig4_debris.png

Note: the catalog is today's state. Pieces catalogued later are counted
from the test date onward, so early months may show more pieces than were
publicly catalogued at that time.

Usage (from project root):  python src/04_debris.py
"""

from datetime import date

import matplotlib

matplotlib.use("Agg")   # draw to files only, no window
import matplotlib.pyplot as plt
import pandas as pd

from common import DATA_RAW, FIGURES, TABLES, spacetrack_query

DESIGNATOR = "1982-092"
TEST_DATE = "2021-11-15"
MEDIA_ESTIMATE = 1500     # pieces reported in media after the test (order of magnitude)

QUERY = f"/basicspacedata/query/class/satcat/INTLDES/~~{DESIGNATOR}/orderby/NORAD_CAT_ID asc/format/csv"


def main():
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    raw_file = DATA_RAW / f"kosmos1408_{date.today().isoformat()}.csv"
    if raw_file.exists():
        print(f"{raw_file.name} already exists - skipping download.")
    else:
        raw_file.write_text(spacetrack_query(QUERY), encoding="utf-8")
        print(f"Saved to {raw_file}")

    df = pd.read_csv(raw_file)
    print(f"\nObjects with designator {DESIGNATOR}: {len(df)}")
    print(df["OBJECT_TYPE"].value_counts().to_string())

    # --- Check the parent satellite ---
    parent = df[df["OBJECT_TYPE"] == "PAYLOAD"]
    print("\nParent object(s):")
    print(parent[["NORAD_CAT_ID", "OBJECT_NAME", "LAUNCH", "DECAY"]].to_string(index=False))

    # --- Debris only ---
    debris = df[df["OBJECT_TYPE"] == "DEBRIS"].copy()
    debris["DECAY"] = pd.to_datetime(debris["DECAY"])
    print(f"\nCatalogued debris pieces: {len(debris)}")
    print(f"Still on orbit today: {debris['DECAY'].isna().sum()}")
    diff = abs(len(debris) - MEDIA_ESTIMATE) / MEDIA_ESTIMATE
    if diff > 0.25:
        print(f"WARNING: differs by {diff:.0%} from media estimate (~{MEDIA_ESTIMATE})")

    # --- Debris on orbit at the end of each month ---
    month_ends = pd.date_range(TEST_DATE, date.today(), freq="ME")
    on_orbit = [
        ((debris["DECAY"].isna()) | (debris["DECAY"] > end)).sum()
        for end in month_ends
    ]
    table = pd.DataFrame({"month_end": month_ends.date, "debris_on_orbit": on_orbit})
    TABLES.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "rq3_debris.csv", index=False)
    print("\nDebris on orbit (every 6th month):")
    print(table.iloc[::6].to_string(index=False))

    # --- Chart ---
    retrieved = raw_file.stem.replace("kosmos1408_", "")
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.plot(month_ends, on_orbit, color="#222222", linewidth=1.8)
    ax.set_ylim(0, max(on_orbit) * 1.1)
    ax.set_ylabel("Debris pieces on orbit")
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Catalogued Kosmos 1408 debris remaining on orbit (end of month)",
                 loc="left", fontweight="bold", fontsize=9)
    fig.text(0.01, 0.01, f"Source: Space-Track.org, retrieved {retrieved}; own analysis. "
             f"ASAT test on {TEST_DATE}.", fontsize=7, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "fig4_debris.png", dpi=300)
    plt.close(fig)
    print(f"\nSaved {TABLES / 'rq3_debris.csv'} and {FIGURES / 'fig4_debris.png'}")


if __name__ == "__main__":
    main()
