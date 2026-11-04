# USA vs Russia Satellite Tracking

Data analysis for the semester project in *Open Source Intelligence* (4IT556, VŠE).
The analysis plan is in [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md).

## Setup

Requires Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in Space-Track credentials
```

## Run

Run the scripts in order from the project root:

```powershell
python src/01_download.py
python src/02_classify.py
python src/03_charts.py
python src/04_debris.py   # optional
```

## Data

- Source: [Space-Track.org](https://www.space-track.org) (SATCAT), account required.
- Raw data are stored locally in `data/raw/` and are **not** committed
  (Space-Track terms do not allow redistribution). Only aggregated tables and
  charts in `output/` are part of the repository.
