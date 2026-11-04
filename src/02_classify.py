"""Step 2 - classify satellites (launch id, category, orbit regime).

Input:
  data/raw/satcat_*.csv          (newest file, from 01_download.py)
  data/raw/iss_deployed_*.csv    (newest file, from 01_download.py)
  data/raw/gcat/psatcat_*.tsv    (newest file, GCAT payload catalog by J. McDowell,
                                  https://planet4589.org/space/gcat/)
  data/raw/gcat/satcat_*.tsv     (GCAT main catalog, real launch dates of ISS-deployed sats)
  manual_overrides.csv           (hand-made corrections, win over everything)

Output:
  data/processed/satellites_classified.csv
  data/processed/unclassified.csv  (category still 'unknown', for manual review)

Category is decided in this order (first match wins, manual override last
so it can overwrite anything):
  1. name rules     (e.g. STARLINK -> starlink, USA xxx -> military)
  2. GCAT 'Class'   (D -> military, C/A -> civil, B -> commercial)
  3. otherwise      -> unknown
  4. manual_overrides.csv overwrites the result

Usage (from project root):  python src/02_classify.py
"""

import pandas as pd

from common import DATA_PROCESSED, DATA_RAW, MANUAL_OVERRIDES, PERIOD_END, PERIOD_START, newest_file

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Name rules: (country, name prefix, category). Checked top to bottom.
NAME_RULES = [
    ("US", "STARLINK", "starlink"),
    ("US", "USA ", "military"),             # US government (mostly NRO/DoD) designation
    ("US", "PRAETORIAN SDA", "military"),   # Space Development Agency constellation
    ("US", "GLOBALSTAR", "commercial"),
    ("US", "SPACEMOBILE", "commercial"),    # AST SpaceMobile
    ("CIS", "COSMOS", "military"),          # Russian military designation
    ("CIS", "RASSVET", "commercial"),       # Bureau 1440 broadband constellation
    ("CIS", "SOYUZ", "civil"),              # crewed ISS spacecraft
    ("CIS", "PROGRESS", "civil"),           # ISS cargo spacecraft
]

# GCAT 'Class' -> our category. Mixed classes containing 'D' (e.g. 'BD') -> military.
GCAT_CLASS_MAP = {
    "D": "military",
    "C": "civil",
    "A": "civil",       # amateur / university satellites
    "B": "commercial",
}

# GLONASS navigation satellites are named COSMOS xxxx. They are run by the
# Russian Ministry of Defence but serve civil users too -> team decision.
GLONASS_CATEGORY = "military"

VALID_CATEGORIES = {"military", "civil", "commercial", "starlink", "unknown"}

# Orbit regime thresholds
EARTH_RADIUS_KM = 6378.137
LEO_MAX_APOGEE_KM = 2000
HEO_MIN_ECCENTRICITY = 0.25
GEO_PERIOD_MIN, GEO_PERIOD_MAX = 1400, 1460   # minutes
GEO_MAX_ECCENTRICITY = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_gcat():
    """Load GCAT payload catalog and return NORAD id, Class and Category."""
    path = newest_file(DATA_RAW / "gcat", "psatcat_*.tsv")
    # Line 1 = header starting with '#', line 2 = '# Updated ...' comment
    gcat = pd.read_csv(path, sep="\t", skiprows=[1], dtype=str)
    gcat.columns = [c.lstrip("#").strip() for c in gcat.columns]
    gcat = gcat.apply(lambda col: col.str.strip())

    # JCAT 'S54247' = object with NORAD number 54247 (other prefixes are not in SATCAT)
    gcat = gcat[gcat["JCAT"].str.match(r"^S\d+$")].copy()
    gcat["NORAD_CAT_ID"] = gcat["JCAT"].str[1:].astype(int)
    gcat = gcat.rename(columns={"Class": "gcat_class", "Category": "gcat_category"})
    print(f"GCAT: {path.name}, {len(gcat)} payloads")
    return gcat[["NORAD_CAT_ID", "gcat_class", "gcat_category"]]


def load_iss_deployed(gcat_payload_ids):
    """Return ISS-deployed payloads whose cargo flight launched in the study period.

    Space-Track gives them the ISS designator and launch date (1998). GCAT's main
    catalog has the real launch date of the cargo flight (LDate) and its
    designator (Launch_Tag), so we take those from GCAT.
    Objects that GCAT does not list as payloads (e.g. items thrown away during
    spacewalks) are dropped.
    """
    iss = pd.read_csv(newest_file(DATA_RAW, "iss_deployed_*.csv"))
    not_payload = ~iss["NORAD_CAT_ID"].isin(gcat_payload_ids)
    print(f"ISS objects dropped (not a payload in GCAT): {not_payload.sum()}")
    iss = iss[~not_payload]
    path = newest_file(DATA_RAW / "gcat", "satcat_*.tsv")
    gcat = pd.read_csv(path, sep="\t", skiprows=[1], dtype=str)
    gcat.columns = [c.lstrip("#").strip() for c in gcat.columns]
    gcat = gcat.apply(lambda col: col.str.strip())
    gcat = gcat[gcat["Satcat"].str.match(r"^\d+$", na=False)].copy()
    gcat["NORAD_CAT_ID"] = gcat["Satcat"].astype(int)

    iss = iss.merge(gcat[["NORAD_CAT_ID", "LDate", "Launch_Tag"]], on="NORAD_CAT_ID", how="left")
    print(f"ISS-deployed payloads (all years): {len(iss)}, without GCAT date: {iss['LDate'].isna().sum()}")

    # GCAT date '2022 Jun  3' (sometimes with time or '?') -> keep year, month, day
    ldate = pd.to_datetime(iss["LDate"].str.split().str[:3].str.join(" "), format="%Y %b %d")
    iss["LAUNCH"] = ldate.dt.strftime("%Y-%m-%d")
    iss = iss[(iss["LAUNCH"] >= PERIOD_START) & (iss["LAUNCH"] <= PERIOD_END)].copy()
    iss["launch_id"] = iss["Launch_Tag"]
    print(f"ISS-deployed payloads launched in study period: {len(iss)}")
    return iss.drop(columns=["LDate", "Launch_Tag"])


def category_from_name(row):
    for country, prefix, category in NAME_RULES:
        if row["COUNTRY"] == country and row["OBJECT_NAME"].startswith(prefix):
            return category
    return None


def category_from_gcat(gcat_class):
    if pd.isna(gcat_class):
        return None
    if "D" in gcat_class:
        return "military"
    return GCAT_CLASS_MAP.get(gcat_class)   # '-' or unknown code -> None


def orbit_regime(row):
    apogee, perigee, period = row["APOGEE"], row["PERIGEE"], row["PERIOD"]
    if pd.isna(apogee) or pd.isna(perigee) or pd.isna(period):
        return "unknown"
    ra = apogee + EARTH_RADIUS_KM
    rp = perigee + EARTH_RADIUS_KM
    e = (ra - rp) / (ra + rp)
    if apogee < LEO_MAX_APOGEE_KM:
        return "LEO"
    if e > HEO_MIN_ECCENTRICITY:
        return "HEO"
    if GEO_PERIOD_MIN <= period <= GEO_PERIOD_MAX and e < GEO_MAX_ECCENTRICITY:
        return "GEO"
    return "MEO"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    satcat_path = newest_file(DATA_RAW, "satcat_*.csv")
    df = pd.read_csv(satcat_path)
    print(f"SATCAT: {satcat_path.name}, {len(df)} records")

    # --- 2a) Launch id: '2025-012A' -> '2025-012' ---
    df["launch_id"] = df["INTLDES"].str.extract(r"^(\d{4}-\d{3})")[0]
    print(f"Records without launch id: {df['launch_id'].isna().sum()}")

    gcat = load_gcat()

    # Add satellites deployed from the ISS (launch id = their cargo flight)
    iss = load_iss_deployed(gcat["NORAD_CAT_ID"])
    df["iss_deployed"] = False
    iss["iss_deployed"] = True
    df = pd.concat([df, iss], ignore_index=True)
    print(f"Total records: {len(df)}")

    # --- 2b) Category ---
    df = df.merge(gcat, on="NORAD_CAT_ID", how="left")
    print(f"Matched in GCAT: {df['gcat_class'].notna().sum()} of {len(df)}")

    by_name = df.apply(category_from_name, axis=1)
    by_gcat = df["gcat_class"].apply(category_from_gcat)

    df["category"] = by_name.fillna(by_gcat).fillna("unknown")
    df["category_source"] = "none"
    df.loc[by_gcat.notna(), "category_source"] = "gcat"
    df.loc[by_name.notna(), "category_source"] = "name"

    # GLONASS = COSMOS satellite with GCAT mission category NAV
    df["is_glonass"] = (
        df["OBJECT_NAME"].str.startswith("COSMOS")
        & df["gcat_category"].fillna("").str.startswith("NAV")
    )
    df.loc[df["is_glonass"], "category"] = GLONASS_CATEGORY
    df.loc[df["is_glonass"], "category_source"] = "glonass"
    print(f"GLONASS satellites: {df['is_glonass'].sum()} -> '{GLONASS_CATEGORY}'")

    # Manual overrides win over everything
    overrides = pd.read_csv(MANUAL_OVERRIDES)
    bad = set(overrides["category"]) - VALID_CATEGORIES
    if bad:
        raise SystemExit(f"Invalid category in manual_overrides.csv: {bad}")
    override_map = overrides.set_index("NORAD_CAT_ID")["category"]
    is_override = df["NORAD_CAT_ID"].isin(override_map.index)
    df.loc[is_override, "category"] = df.loc[is_override, "NORAD_CAT_ID"].map(override_map)
    df.loc[is_override, "category_source"] = "manual"
    print(f"Manual overrides applied: {is_override.sum()}")

    # Check: do name rules agree with GCAT? (useful for methodology)
    both = df[(df["category_source"] == "name") & by_gcat.notna()]
    agree = (by_name[both.index] == by_gcat[both.index]) | (both["category"] == "starlink")
    print(f"Name rule vs GCAT agreement: {agree.sum()} of {len(both)}")
    disagree = both[~agree]
    if len(disagree):
        print(disagree.groupby(["COUNTRY", "category", "gcat_class"]).size().to_string())

    # --- 2c) Orbit regime ---
    df["orbit"] = df.apply(orbit_regime, axis=1)

    # --- 2d) Checks ---
    print("\nCategory source:")
    print(df["category_source"].value_counts().to_string())
    print("\nCountry x category:")
    print(pd.crosstab(df["COUNTRY"], df["category"], margins=True).to_string())
    print("\nCountry x orbit:")
    print(pd.crosstab(df["COUNTRY"], df["orbit"], margins=True).to_string())
    # Starlink is ~85 % of all records, so sample from the rest to make the check useful
    print("\n20 random non-Starlink rows for manual check:")
    cols = ["OBJECT_NAME", "COUNTRY", "category", "category_source", "orbit"]
    non_starlink = df[df["category"] != "starlink"]
    print(non_starlink[cols].sample(20, random_state=42).to_string(index=False))

    # --- Save ---
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "satellites_classified.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} records to {out}")

    unclassified = df[df["category"] == "unknown"]
    unclassified[["NORAD_CAT_ID", "OBJECT_NAME", "INTLDES", "COUNTRY", "LAUNCH",
                  "gcat_class", "gcat_category"]].to_csv(
        DATA_PROCESSED / "unclassified.csv", index=False)
    print(f"Unclassified: {len(unclassified)} -> data/processed/unclassified.csv")


if __name__ == "__main__":
    main()
