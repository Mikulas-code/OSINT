# USA vs Russia Satellite Tracking

Data analysis for the semester project in *Open Source Intelligence* (4IT556, VŠE).
The analysis plan is in [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md).

## Setup

Requires Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in your Space-Track credentials
```

The GCAT catalogs are downloaded manually (no login needed):

```powershell
mkdir data\raw\gcat
curl.exe -o data\raw\gcat\psatcat_YYYY-MM-DD.tsv https://planet4589.org/space/gcat/tsv/cat/psatcat.tsv
curl.exe -o data\raw\gcat\satcat_YYYY-MM-DD.tsv https://planet4589.org/space/gcat/tsv/cat/satcat.tsv
```

## Run

Run the scripts in order from the project root:

| Script | What it does | Output |
|---|---|---|
| `src/01_download.py` | downloads US and Russian payloads from Space-Track SATCAT (+ ISS-deployed payloads) | `data/raw/satcat_<date>.csv`, `data/raw/iss_deployed_<date>.csv` |
| `src/02_classify.py` | adds launch id, category (military / civil / commercial / Starlink) and orbit regime | `data/processed/satellites_classified.csv` |
| `src/03_charts.py` | RQ1/RQ2 tables and charts, evaluates H1 | `output/tables/rq1_*, rq2_*`, `output/figures/fig1–3` |
| `src/04_debris.py` | RQ3: Kosmos 1408 debris on orbit over time | `output/tables/rq3_debris.csv`, `output/figures/fig4_debris.png` |

Downloads run only once per day (if today's file exists, Space-Track is not contacted).

## Data sources

- **Space-Track.org** SATCAT (account required), retrieved **2026-11-04**.
- **GCAT** by Jonathan McDowell (planet4589.org), `psatcat.tsv` and `satcat.tsv`, version updated 2026-11-02.
  Used to classify satellites whose name does not reveal the operator and to date ISS-deployed satellites.
- Raw and processed data are stored locally in `data/` and are **not** committed
  (Space-Track terms do not allow redistribution). Only aggregated tables and
  charts in `output/` are part of the repository.

## Method in brief

- **Study period:** launches from 2022-02-24 (start of the Russian invasion of Ukraine) to 2026-09-30.
  Payloads only; decayed satellites are included. Russia = Space-Track country code `CIS`.
- **ISS-deployed satellites:** Space-Track gives them the ISS designator and launch date (1998-067, 1998-11-20).
  They are added separately; launch date and launch id are taken from their cargo flight (GCAT `LDate`, `Launch_Tag`).
  Objects GCAT does not list as payloads (items jettisoned during spacewalks) are dropped. 26 satellites added (21 US, 5 Russia).
- **Orbital launches** = distinct launches (international designator `YYYY-NNN`) carrying at least
  one payload of the country, regardless of the rocket's country.
- **Category**, first match wins:
  1. name rules (`STARLINK` → Starlink, `USA xxx` / `PRAETORIAN SDA` / `COSMOS` → military, a few named commercial and civil series),
  2. GCAT `Class` (D → military, C/A → civil, B → commercial),
  3. otherwise unknown; `manual_overrides.csv` overrides everything.
  GLONASS (COSMOS with GCAT category NAV) is counted as military (`GLONASS_CATEGORY` in `02_classify.py`).
  Name rules agree with GCAT in 10 746 of 10 747 cases.
- **Orbit regime** from apogee, perigee and period: LEO (apogee < 2 000 km), HEO (eccentricity > 0.25),
  GEO (period 1 400–1 460 min, e < 0.05), otherwise MEO; unknown if orbital data are missing
  (deep-space missions and 7 US military satellites without published orbits).
  The regime is based on the current or last known orbit, not the orbit at launch.
- **H1 test:** LEO share = LEO / all payloads in the group (unknown orbits included, conservative).
  Confirmed if USA excl. Starlink, Russia, US military and Russian military are all above 50 %;
  partially confirmed if only some are; rejected if none.
- **Limitation:** GCAT does not yet contain objects launched after ~11 July 2026 (new 6-digit NORAD numbers);
  these were classified by name rules only, have no mission type, and GLONASS satellites among them would not be
  recognised (no effect now, COSMOS is military either way).

## Main results (retrieved 2026-11-04)

**RQ1 – payloads launched 2022-02-24 to 2026-09-30**

|  | USA | USA excl. Starlink | Russia |
|---|---|---|---|
| Orbital launches | 588 | 209 | 84 |
| Payloads total | 12 531 | 1 718 | 185 |
| Military | 514 | 514 | 71 |
| Civil | 98 | 98 | 63 |
| Commercial | 1 094 | 1 094 | 49 |
| Starlink | 10 813 | – | – |
| Unknown | 12 | 12 | 2 |

**RQ2 – H1 (both countries focus on LEO): confirmed, also for military satellites.**
LEO share: USA 99.2 %, USA excl. Starlink 94.4 %, Russia 88.1 %, US military 90.5 %, Russian military 80.3 %.

**RQ3 – Kosmos 1408 ASAT test (2021-11-15):** 1 806 catalogued debris pieces (designator 1982-092).
About half had decayed by mid-2022; 4 pieces remain on orbit at retrieval date.
