"""Step 3 - produce tables and charts for RQ1 and RQ2.

Input:   data/processed/satellites_classified.csv  (from 02_classify.py)
Output:  output/tables/rq1_counts.csv, output/tables/rq2_orbits.csv
         output/figures/fig1_quarterly.png, fig2_orbits.png, fig3_scatter.png
         + evaluation of hypothesis H1 printed to the console

Charts use grey shades + hatching so they stay readable in black-and-white print.

Usage (from project root):  python src/03_charts.py
"""

import matplotlib

matplotlib.use("Agg")   # draw to files only, no window
import matplotlib.pyplot as plt
import pandas as pd

from common import DATA_PROCESSED, DATA_RAW, FIGURES, PERIOD_END, PERIOD_START, TABLES, newest_file

DPI = 300
LEO_THRESHOLD = 0.5      # H1: LEO share must be above 50 %

# Retrieval date for the source note = date in the raw SATCAT file name
RETRIEVED = newest_file(DATA_RAW, "satcat_*.csv").stem.replace("satcat_", "")
SOURCE_NOTE = f"Source: Space-Track.org, retrieved {RETRIEVED}; GCAT (J. McDowell); own analysis."

COUNTRY_LABEL = {"US": "USA", "CIS": "Russia"}

# Common look: small fonts for a report page, light grid, no top/right frame
plt.rcParams.update({
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "hatch.linewidth": 0.6,
})


def add_source(fig):
    fig.text(0.01, 0.01, SOURCE_NOTE, fontsize=7, color="#555555", ha="left", va="bottom")


def groups(df):
    """The groups compared in RQ1/RQ2 (name -> subset of rows)."""
    us = df[df["COUNTRY"] == "US"]
    ru = df[df["COUNTRY"] == "CIS"]
    return {
        "USA": us,
        "USA excl. Starlink": us[us["category"] != "starlink"],
        "Russia": ru,
        "US military": us[us["category"] == "military"],
        "Russian military": ru[ru["category"] == "military"],
    }


# ---------------------------------------------------------------------------
# RQ1
# ---------------------------------------------------------------------------

def rq1_table(df):
    """Counts of launches and payloads by category for USA, USA excl. Starlink, Russia.

    'Orbital launches' = number of distinct launches (launch_id) that carried at
    least one payload of that country - not the country of the rocket.
    """
    g = groups(df)
    table = {}
    for name in ["USA", "USA excl. Starlink", "Russia"]:
        sub = g[name]
        cats = sub["category"].value_counts()
        table[name] = {
            "Orbital launches": sub["launch_id"].nunique(),
            "Payloads total": len(sub),
            "Military": cats.get("military", 0),
            "Civil": cats.get("civil", 0),
            "Commercial": cats.get("commercial", 0),
            "Starlink": cats.get("starlink", 0),
            "Unknown": cats.get("unknown", 0),
        }
    table = pd.DataFrame(table)
    table.to_csv(TABLES / "rq1_counts.csv")
    print("RQ1 counts:\n" + table.to_string() + "\n")


CATEGORIES = ["military", "civil", "commercial", "starlink", "unknown"]


def rq1_yearly(df):
    """Payloads per year by country and category (2022 starts on PERIOD_START)."""
    df = df.assign(year=df["LAUNCH"].str[:4],
                   country=df["COUNTRY"].map(COUNTRY_LABEL))
    table = pd.crosstab([df["country"], df["category"]], df["year"], margins=True, margins_name="Total")
    table = table.reindex([(c, cat) for c in ["USA", "Russia"] for cat in CATEGORIES] + [("Total", "")])
    table = table.dropna(how="all").fillna(0).astype(int)
    table.to_csv(TABLES / "rq1_yearly.csv")
    print("RQ1 payloads per year:\n" + table.to_string() + "\n")


# GCAT mission codes -> readable names. GCAT adds '?' (uncertain) or '*' to some
# codes; we keep only the main code before these marks.
MISSIONS = {
    "IMG": "Imaging / reconnaissance",
    "SIG": "Signals intelligence",
    "COM": "Communications",
    "EW": "Missile early warning",
    "NAV": "Navigation",
    "TECH": "Technology demonstration",
}


def rq1_military_missions(df):
    """Military satellites by mission type (from GCAT 'Category')."""
    mil = df[df["category"] == "military"].copy()
    code = mil["gcat_category"].fillna("").str.split("/").str[0].str.rstrip("?*")
    mil["mission"] = code.map(MISSIONS).fillna("Other / not in GCAT")
    table = pd.crosstab(mil["mission"], mil["COUNTRY"].map(COUNTRY_LABEL))[["USA", "Russia"]]
    order = list(MISSIONS.values()) + ["Other / not in GCAT"]
    table = table.reindex(order, fill_value=0)
    table.loc["Total"] = table.sum()
    table.to_csv(TABLES / "rq1_military_missions.csv")
    print("RQ1 military satellites by mission:\n" + table.to_string() + "\n")


def fig1_quarterly(df):
    """Payloads launched per quarter, with and without Starlink (two panels)."""
    df = df.copy()
    df["quarter"] = pd.to_datetime(df["LAUNCH"]).dt.to_period("Q")
    quarters = pd.period_range(PERIOD_START, PERIOD_END, freq="Q")

    def per_quarter(sub):
        return sub.groupby("quarter").size().reindex(quarters, fill_value=0)

    us = df[df["COUNTRY"] == "US"]
    ru = df[df["COUNTRY"] == "CIS"]
    panels = [
        ("a) Including Starlink", per_quarter(us), per_quarter(ru)),
        ("b) Excluding Starlink", per_quarter(us[us["category"] != "starlink"]), per_quarter(ru)),
    ]

    fig, axes = plt.subplots(2, 1, figsize=(6.5, 5.5), sharex=True)
    x = range(len(quarters))
    w = 0.4
    for ax, (title, us_q, ru_q) in zip(axes, panels):
        ax.bar([i - w / 2 for i in x], us_q, w, label="USA", color="#333333")
        ax.bar([i + w / 2 for i in x], ru_q, w, label="Russia", color="#bbbbbb",
               hatch="////", edgecolor="#555555", linewidth=0.4)
        ax.set_title(title, loc="left", fontsize=9, fontweight="bold")
        ax.set_ylabel("Payloads launched")
    axes[0].legend(frameon=False, loc="upper left")
    labels = [f"{q.year} Q{q.quarter}" for q in quarters]
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels, rotation=60, ha="right", fontsize=7.5)
    fig.suptitle("US and Russian payloads launched per quarter", fontweight="bold", x=0.01, ha="left")
    fig.text(0.99, 0.01, f"First quarter starts {PERIOD_START}.", fontsize=7, color="#555555", ha="right")
    add_source(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "fig1_quarterly.png", dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# RQ2
# ---------------------------------------------------------------------------

ORBITS = ["LEO", "MEO", "HEO", "GEO", "unknown"]
ORBIT_STYLE = {   # grey shade + hatch, distinguishable in black-and-white print
    "LEO": dict(color="#333333", hatch=""),
    "MEO": dict(color="#888888", hatch=""),
    "HEO": dict(color="#bbbbbb", hatch="////"),
    "GEO": dict(color="#dddddd", hatch=""),
    "unknown": dict(color="#ffffff", hatch="...."),
}


def rq2_table(df):
    rows = {name: sub["orbit"].value_counts().reindex(ORBITS, fill_value=0)
            for name, sub in groups(df).items()}
    counts = pd.DataFrame(rows).T
    counts["n"] = counts.sum(axis=1)
    shares = counts[ORBITS].div(counts["n"], axis=0) * 100

    out = counts.copy()
    for o in ORBITS:
        out[f"{o} %"] = shares[o].round(1)
    out.to_csv(TABLES / "rq2_orbits.csv")
    print("RQ2 orbit regimes:\n" + out.to_string() + "\n")
    return counts, shares


def fig2_orbits(counts, shares):
    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = range(len(shares))
    bottom = [0] * len(shares)
    for o in ORBITS:
        ax.bar(x, shares[o], bottom=bottom, label=o, edgecolor="#333333",
               linewidth=0.5, width=0.6, **ORBIT_STYLE[o])
        bottom = [b + v for b, v in zip(bottom, shares[o])]
    for i, n in enumerate(counts["n"]):
        ax.text(i, 102, f"n = {n:,}".replace(",", " "), ha="center", fontsize=8)
    ax.set_xticks(list(x))
    # Two-line labels so the longer group names do not overlap
    ax.set_xticklabels([name.replace(" ", "\n", 1) for name in shares.index])
    ax.set_ylim(0, 110)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Share of payloads (%)")
    ax.legend(title="Orbit", frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.set_title("Orbital regimes of US and Russian payloads", loc="left", fontweight="bold")
    add_source(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGURES / "fig2_orbits.png", dpi=DPI)
    plt.close(fig)


def evaluate_h1(shares):
    """H1: both USA and Russia focus on LEO (LEO share > 50 %)."""
    leo = shares["LEO"] / 100
    print("H1 - share of LEO by group:")
    for name, value in leo.items():
        print(f"  {name:20s} {value:6.1%}")

    overall = leo["USA excl. Starlink"] > LEO_THRESHOLD and leo["Russia"] > LEO_THRESHOLD
    military = leo["US military"] > LEO_THRESHOLD and leo["Russian military"] > LEO_THRESHOLD
    if overall and military:
        result = "CONFIRMED (also for military satellites)"
    elif overall:
        result = "PARTIALLY CONFIRMED (holds overall, not for military satellites)"
    else:
        result = "REJECTED"
    print(f"H1 result: {result}\n")


def fig3_scatter(df):
    """Inclination vs apogee. Starlink is left out, it would cover everything."""
    df = df[(df["orbit"] != "unknown") & (df["category"] != "starlink")]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    styles = {"US": dict(marker="o", facecolors="none", edgecolors="#333333"),
              "CIS": dict(marker="^", color="#000000")}
    for country, style in styles.items():
        sub = df[df["COUNTRY"] == country]
        ax.scatter(sub["INCLINATION"], sub["APOGEE"], s=10, linewidths=0.5, alpha=0.7,
                   label=f"{COUNTRY_LABEL[country]} (n = {len(sub)})", **style)
    ax.set_yscale("log")
    ax.axhline(2000, color="#777777", linestyle="--", linewidth=0.7)
    ax.text(0, 2300, "LEO limit (2 000 km)", fontsize=7, color="#555555")
    ax.set_xlabel("Inclination (deg)")
    ax.set_ylabel("Apogee altitude (km, log scale)")
    ax.grid(axis="x")
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Orbits of US (excl. Starlink) and Russian payloads", loc="left", fontweight="bold")
    add_source(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGURES / "fig3_scatter.png", dpi=DPI)
    plt.close(fig)


def main():
    df = pd.read_csv(DATA_PROCESSED / "satellites_classified.csv")
    print(f"Loaded {len(df)} classified records (retrieved {RETRIEVED})\n")
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    rq1_table(df)
    rq1_yearly(df)
    rq1_military_missions(df)
    fig1_quarterly(df)
    counts, shares = rq2_table(df)
    fig2_orbits(counts, shares)
    evaluate_h1(shares)
    fig3_scatter(df)
    print(f"Figures saved to {FIGURES}, tables to {TABLES}")


if __name__ == "__main__":
    main()
