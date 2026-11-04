# Analysis Plan: USA vs Russia Satellite Tracking

Zadání datové analýzy pro semestrální projekt z předmětu Open Source Intelligence (4IT556, VŠE, ZS 2026/2027). Tento soubor slouží jako podklad pro Claude Code.

## Kontext

Tým zkoumá satelitní aktivitu USA a Ruska. Datová analýza odpovídá na tyto výzkumné otázky:

- **RQ1:** How many satellites did the US and Russia launch between 24 February 2022 and 30 September 2026, and how many of them can be identified as military, civil or commercial from open sources?
- **RQ2 (hypotéza H1):** Between 24 February 2022 and 30 September 2026, both the USA and Russia launched the majority of their satellites (including military ones) into LEO.
- **RQ3:** Were there any documented attacks on satellites between 2021 and 2026, and what were their consequences? → hlavně rešerše; vlastní data o troskách po ruském ASAT testu z listopadu 2021 slouží jako podpora (důsledky). Případně později rozšířit o další incidenty.
- **RQ4:** Which space incidents between 2021 and 2026 increased tension between the USA and Russia?

RQ4 je čistě rešeršní, analýza ji neřeší.

## Pravidla pro práci

- Kód má být jednoduchý a okomentovaný. Tým ho musí umět vysvětlit u prezentace.
- Přihlašovací údaje jsou pouze v `.env` a nikdy se necommitují.
- Data ze Space-Tracku se stahují jednou a ukládají se lokálně, opakované dotazy nejsou potřeba. Respektovat limity API (podle dokumentace Space-Track, aktuálně ověřit; orientačně max. 30 dotazů za minutu a 300 za hodinu).
- Data nepatří do gitu (`data/raw/` i `data/processed/` v `.gitignore`, i zpracovaný soubor obsahuje jednotlivé záznamy). Podmínky Space-Track neumožňují jejich další šíření; do reportu jdou jen agregace a grafy.
- Nic si nedomýšlet. Pokud nějaké pole v datech chybí nebo vypadá jinak, než je popsáno níže, zastavit se a vypsat skutečné hlavičky a ukázkové řádky.
- Po každém kroku vypsat počty záznamů (kolik staženo, kolik vyřazeno a proč).

## Struktura projektu

```
OSINT/
├── .env                    # SPACETRACK_USER, SPACETRACK_PASS (není v gitu)
├── .env.example            # šablona pro .env
├── .gitignore              # .env, data/raw/, data/processed/, .venv/
├── requirements.txt        # pandas, requests, matplotlib, python-dotenv
├── manual_overrides.csv    # ruční klasifikace sporných družic (NORAD_CAT_ID,category,note)
├── data/
│   ├── raw/                # stažená data s datem v názvu souboru
│   └── processed/          # vyčištěná a klasifikovaná data (také mimo git)
├── src/
│   ├── common.py           # sdílené cesty a sledované období
│   ├── 01_download.py
│   ├── 02_classify.py
│   ├── 03_charts.py
│   └── 04_debris.py        # volitelné
└── output/                 # jen agregace a grafy -> do gitu
    ├── figures/
    └── tables/
```

## Krok 1: Stažení dat (`01_download.py`)

Přihlášení: `POST https://www.space-track.org/ajaxauth/login` s parametry `identity` a `password` (z `.env`), dále používat stejnou session.

Dotaz na družice (payloady) USA a Ruska vypuštěné ve sledovaném období:

```
https://www.space-track.org/basicspacedata/query/class/satcat/LAUNCH/2022-02-24--2026-09-30/OBJECT_TYPE/PAYLOAD/COUNTRY/US,CIS/format/csv
```

- `CIS` je v Space-Tracku označení pro Rusko (bývalé SSSR).
- Ponechat i družice, které už zanikly (vyplněné `DECAY`). Otázka zní, kolik se jich vypustilo.
- Uložit jako `data/raw/satcat_YYYY-MM-DD.csv` (datum stažení, uvádí se v metodice).

Očekávaná důležitá pole: `NORAD_CAT_ID`, `OBJECT_NAME`, `INTLDES`, `COUNTRY`, `LAUNCH`, `SITE`, `DECAY`, `PERIOD`, `INCLINATION`, `APOGEE`, `PERIGEE`. Ověřit, že opravdu existují.

## Krok 2: Klasifikace (`02_classify.py`)

### 2a) Číslo startu

Z `INTLDES` (např. `2025-012A`) vzít část před písmenem (`2025-012`) → sloupec `launch_id`. Počet startů = počet unikátních `launch_id` pro danou zemi.

### 2b) Kategorie družice

Sloupec `category` s hodnotami `military`, `civil`, `commercial`, `starlink`, `unknown`.

Pravidla podle `OBJECT_NAME`, v tomto pořadí:

| Země | Pravidlo | Kategorie |
|---|---|---|
| US | název začíná `STARLINK` | `starlink` |
| US | název začíná `USA ` | `military` |
| CIS | název začíná `COSMOS` | `military` |
| obě | záznam je v `manual_overrides.csv` | hodnota ze souboru (má přednost před vším výše) |
| obě | ostatní | `unknown` |

Doplnění `unknown`: zkusit GCAT od Jonathana McDowella (planet4589.org, soubor s katalogem payloadů). Nejdřív stáhnout, vypsat hlavičky a ukázat, které pole obsahuje kategorii nebo vlastníka družice; teprve potom navrhnout mapování. Spojovat přes NORAD číslo. Co zůstane nezařazené, vypsat do `output/tables/unclassified.csv` k ruční kontrole.

**Otevřené rozhodnutí:** ruské navigační družice GLONASS mají v katalogu název `COSMOS xxxx`. Nastavit konstantu `GLONASS_CATEGORY` (výchozí `military`) a GLONASS družice identifikovat přes GCAT nebo ruční seznam. Výsledné rozhodnutí tým uvede v metodice.

### 2c) Orbitální režim

Sloupec `orbit` z `APOGEE`, `PERIGEE` (km nad Zemí) a `PERIOD` (min). Výpočet excentricity:

```
ra = APOGEE + 6378.137
rp = PERIGEE + 6378.137
e  = (ra - rp) / (ra + rp)
```

Pravidla, v tomto pořadí:

1. chybí orbitální data → `unknown`
2. `APOGEE < 2000` → `LEO`
3. `e > 0.25` → `HEO`
4. `1400 <= PERIOD <= 1460` a `e < 0.05` → `GEO`
5. ostatní → `MEO`

Prahy mít jako konstanty na začátku skriptu.

### 2d) Kontrola

- Vypsat 20 náhodných řádků (název, země, kategorie, orbita) k ruční kontrole.
- Vypsat kontingenční tabulku země × kategorie a země × orbita.
- Uložit `data/processed/satellites_classified.csv`.

## Krok 3: Výstupy (`03_charts.py`)

Popisky grafů anglicky (report je v angličtině). Grafy musí být čitelné i při černobílém tisku (odstíny šedi nebo šrafování, ne jen barva). Ukládat jako PNG v rozlišení 300 dpi. Do popisku nebo poznámky pod grafem uvést zdroj: „Source: Space-Track.org, retrieved [date]; own analysis.“

### RQ1

**Tabulka `rq1_counts.csv`:** řádky = orbital launches, payloads total, military, civil, commercial, Starlink, unknown; sloupce = USA, USA excl. Starlink, Russia.

**Graf 1 `fig1_quarterly.png`:** počet vypuštěných družic po čtvrtletích (Q1/2022–Q3/2026; ~56 měsíců by bylo po měsících nečitelné). Dva panely nebo dvě verze: s Starlinkem a bez něj, jinak budou ruská čísla v grafu neviditelná.

### RQ2

**Graf 2 `fig2_orbits.png`:** skládaný sloupcový graf podílu orbitálních režimů (%) pro skupiny: USA, USA excl. Starlink, Russia, US military, Russian military. Nad sloupce napsat absolutní počty (n = …).

**Tabulka `rq2_orbits.csv`:** stejná data v číslech.

**Vyhodnocení hypotézy H1:** skript vypíše podíl LEO pro každou skupinu a výsledek pravidla: H1 je potvrzena, pokud je podíl LEO nad 50 % u USA (bez Starlinku) i u Ruska. Jinak zamítnuta nebo částečně potvrzena (např. platí celkově, ale ne pro vojenské družice).

**Graf 3 `fig3_scatter.png` (volitelný):** inklinace (osa x) proti výšce apogea (osa y, logaritmická), tvar nebo odstín bodu podle země.

## Krok 4: Trosky Kosmos 1408 (`04_debris.py`, volitelné, RQ3)

Ruský ASAT test 15. 11. 2021 zničil družici Kosmos 1408. Úlomky mají v katalogu stejné mezinárodní označení startu jako původní družice (ověřit, předpoklad je `1982-092`).

```
https://www.space-track.org/basicspacedata/query/class/satcat/INTLDES/~~1982-092/OBJECT_TYPE/DEBRIS/format/csv
```

- Pro každý měsíc od 11/2021 do posledního dostupného spočítat, kolik úlomků bylo na oběžné dráze (`DECAY` prázdné nebo pozdější než konec měsíce).
- Kontrola: celkový počet katalogizovaných úlomků porovnat s hodnotami uváděnými v médiích (řádově 1 500). Pokud se výrazně liší, vypsat to.
- **Graf 4 `fig4_debris.png`:** počet úlomků na oběžné dráze v čase.

## Výsledek pro report

| Výstup | RQ | Kapitola reportu |
|---|---|---|
| `rq1_counts.csv` | RQ1 | 4.1.1 (Table 3) |
| `fig1_quarterly.png` | RQ1 | 4.1.1 |
| `fig2_orbits.png`, `rq2_orbits.csv` | RQ2 | 4.2 |
| `fig3_scatter.png` (volitelné) | RQ2 | 4.2 |
| `fig4_debris.png` (volitelné) | RQ3 | 4.3.1 |

Na konci vytvořit krátké `README.md`: jak skripty spustit, odkud data jsou, datum stažení a hlavní čísla. Poslouží jako podklad pro Přílohu A a kapitoly 3.2 a 3.3.
