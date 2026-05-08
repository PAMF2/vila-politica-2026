#!/usr/bin/env python3
"""Phase 4: Cross-country generalization extended to 4 new electoral cycles.

Extends scripts/cross_country_validation.py with:
  - France 2022 presidential (Macron vs Le Pen runoff)
  - Argentina 2023 presidential (Milei vs Massa runoff)
  - Brazil 2014 presidential (Dilma vs Aecio runoff)
  - US 2022 midterm governor races (top swing states)

Data sources (raw HTML/CSV under data/cross_country/raw_extended/):
  - Wikipedia: "Opinion polling for the 2022 French presidential election"
  - Wikipedia: "Opinion polling for the 2023 Argentine general election"
  - Wikipedia (PT): "Pesquisas de opiniao para a eleicao presidencial no Brasil em 2014"
  - FiveThirtyEight governor_polls.csv (2022 cycle, via Wayback Machine)

Pipeline per cycle:
  1. Parse poll-level rows, build paired (winner=1, loser=0) CSV in
     data/backtest/{cycle}.csv with the legacy schema.
  2. Filter T <= 30 days from election (matches BR/US pipelines).
  3. LOSO/year-fold leak-safe CV; no_mrp vs mrp_w36; results land in
     data/cross_country_extended.json.

If a source is absent or fails to parse, the cycle is marked
status="data_unavailable" and skipped, never synthesised.

Output:
  data/backtest/fr_2022_president.csv
  data/backtest/ar_2023_president.csv
  data/backtest/br_2014_president.csv
  data/backtest/us_2022_midterms.csv
  data/cross_country_extended.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.political_cohort import (
    fit_cohorts_political,
    predict_political,
    state_baseline_p,
    lead_bin,
    days_bin,
)

RAW_DIR = ROOT / "data" / "cross_country" / "raw_extended"
OUT_DIR = ROOT / "data" / "backtest"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = ROOT / "data" / "cross_country_extended.json"

DAYS_FILTER = 30
W_STATE = 0.36
W_LINZER = 0.5
SIGMA_INT = 4.0
SIGMA_SLO = 0.05
STEIN_SHRINK = 0.05

FIELDNAMES = [
    "evento_id", "data", "contexto", "uf", "ano", "turno", "vencedor",
    "partido", "incumbente", "poll_lead_pp", "outcome_real",
    "probabilidade_prior", "outcome_framing",
]

# ------------------------------------------------------------------ helpers ---


def _strip_html(s: str) -> str:
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&#160;", " ")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _pct(s: str) -> float | None:
    s = _strip_html(s)
    s = s.replace("%", "").replace(",", ".").strip()
    s = re.sub(r"\([^)]*\)", "", s).strip()
    if not s or s in {"-", "--", "?"}:
        return None
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _english_month_date(s: str, default_year: int) -> date | None:
    """Parse '21-22 Apr 2022' or '5-9 November 2023' -> last day."""
    s = _strip_html(s)
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
              "January": 1, "February": 2, "March": 3, "April": 4, "June": 6,
              "July": 7, "August": 8, "September": 9, "October": 10,
              "November": 11, "December": 12}
    # try 'd Mon YYYY' or 'd-d Mon YYYY' or 'd Mon-d Mon YYYY'
    m = re.search(r"(\d{1,2})\s*(?:-|to)?\s*\d*\s*"
                  r"([A-Za-z]+)\s+(\d{4})", s)
    if m:
        d_str, mon_str, year_str = m.groups()
        mon = months.get(mon_str[:4].rstrip("."), months.get(mon_str, None))
        if mon:
            try:
                return date(int(year_str), mon, int(d_str))
            except ValueError:
                pass
    # try 'd-d Mon YYYY' end-day variant
    m2 = re.search(r"\d{1,2}\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m2:
        d_str, mon_str, year_str = m2.groups()
        mon = months.get(mon_str, months.get(mon_str[:3]))
        if mon:
            try:
                return date(int(year_str), mon, int(d_str))
            except ValueError:
                pass
    # 'd Mon-d Mon YYYY' return last
    m3 = re.search(r"\d{1,2}\s+[A-Za-z]+\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m3:
        d_str, mon_str, year_str = m3.groups()
        mon = months.get(mon_str, months.get(mon_str[:3]))
        if mon:
            try:
                return date(int(year_str), mon, int(d_str))
            except ValueError:
                pass
    return None


# --------------------------------------------------- France 2022 (runoff) ---

FR_ELECTION = "2022-04-24"


def build_fr_2022(html_path: Path, out_csv: Path) -> dict:
    """Parse 'Macron vs. Le Pen' second-round table. Each poll yields 2
    paired rows (Macron=winner=1, Le Pen=loser=0)."""
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "FR HTML missing"}
    html = html_path.read_text()
    m = re.search(r'<h3 id="Macron_vs._Le_Pen">.*?(?=<h[23]\s)',
                  html, flags=re.DOTALL)
    if not m:
        return {"status": "data_unavailable", "note": "Macron vs Le Pen section not found"}
    section = m.group()
    tab_m = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                      section, flags=re.DOTALL)
    if not tab_m:
        return {"status": "data_unavailable", "note": "FR runoff table not found"}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tab_m.group(), flags=re.DOTALL)

    election_dt = date.fromisoformat(FR_ELECTION)
    out_rows = []
    n_input = 0
    n_used = 0
    skipped = []
    # Skip header rows: first 3 are headers (rowspan=3 + party row + colour row).
    # Then row index 3 onward, skipping the "2022 election" reference row.
    for raw in rows[3:]:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", raw, flags=re.DOTALL)
        if len(cells) < 6:
            continue
        n_input += 1
        pollster = _strip_html(cells[0])
        if not pollster or "election" in pollster.lower():
            continue  # reference row
        date_txt = _strip_html(cells[1])
        d = _english_month_date(date_txt, 2022)
        if d is None:
            skipped.append(("date_unparsed", date_txt[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        # cells: [pollster, date, sample, abstention, macron, lepen, ...]
        macron_pct = _pct(cells[4])
        lepen_pct = _pct(cells[5])
        if macron_pct is None or lepen_pct is None:
            skipped.append(("pct_missing", pollster))
            continue
        lead = macron_pct - lepen_pct
        datestr = d.isoformat()
        ctx_macron = (f"Emmanuel Macron (LREM) vs Marine Le Pen (RN) "
                      f"runoff in France ({pollster}, {datestr})")
        ctx_lepen = (f"Marine Le Pen (RN) vs Emmanuel Macron (LREM) "
                     f"runoff in France ({pollster}, {datestr})")
        # Macron won (58.55%); incumbent (LREM was governing).
        out_rows.append({
            "evento_id": f"fr2022_{datestr}_{re.sub('[^a-z0-9]', '', pollster.lower())[:14]}_macron",
            "data": datestr,
            "contexto": ctx_macron,
            "uf": "FR",
            "ano": 2022,
            "turno": 2,
            "vencedor": "Emmanuel Macron",
            "partido": "LREM",
            "incumbente": 1,
            "poll_lead_pp": round(lead, 2),
            "outcome_real": 1,
            "probabilidade_prior": round(0.5 + lead / 80.0, 3),
            "outcome_framing": ctx_macron,
        })
        out_rows.append({
            "evento_id": f"fr2022_{datestr}_{re.sub('[^a-z0-9]', '', pollster.lower())[:14]}_lepen",
            "data": datestr,
            "contexto": ctx_lepen,
            "uf": "FR",
            "ano": 2022,
            "turno": 2,
            "vencedor": "Emmanuel Macron",
            "partido": "RN",
            "incumbente": 0,
            "poll_lead_pp": round(-lead, 2),
            "outcome_real": 0,
            "probabilidade_prior": round(0.5 - lead / 80.0, 3),
            "outcome_framing": ctx_lepen,
        })
        n_used += 1

    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input,
        "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2022 French presidential election (Macron vs Le Pen)",
    }


# ----------------------------------------------- Argentina 2023 (runoff) ---

AR_ELECTION = "2023-11-19"


def build_ar_2023(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "AR HTML missing"}
    html = html_path.read_text()
    m = re.search(r'<h3 id="After_the_primaries">.*?(?=<h[23]\s)',
                  html, flags=re.DOTALL)
    if not m:
        return {"status": "data_unavailable",
                "note": "After_the_primaries section not found"}
    section = m.group()
    tab_m = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                      section, flags=re.DOTALL)
    if not tab_m:
        return {"status": "data_unavailable", "note": "AR runoff table not found"}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tab_m.group(), flags=re.DOTALL)

    election_dt = date.fromisoformat(AR_ELECTION)
    out_rows = []
    n_input = 0
    n_used = 0
    skipped = []
    # When the wiki table uses rowspan=N on a date cell, subsequent <tr> rows
    # share that date but emit one fewer <td>. Track last_date and infer.
    last_date_str: str | None = None
    last_date: date | None = None
    for raw in rows[2:]:  # skip 2 header rows (party row, candidate row)
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", raw, flags=re.DOTALL)
        if len(cells) < 5:
            continue
        n_input += 1
        # Try to parse first cell as date. If it parses, the row has the date
        # column. Otherwise, assume rowspan continuation -> reuse last_date and
        # shift columns left by 1.
        first_txt = _strip_html(cells[0])
        if "election" in first_txt.lower() or "general" in first_txt.lower():
            continue
        d = _english_month_date(first_txt, 2023)
        if d is not None:
            offset = 0
            last_date = d
            last_date_str = first_txt
        elif last_date is not None:
            # rowspan continuation: cells[0] is the pollster
            d = last_date
            offset = -1
        else:
            skipped.append(("date_unparsed", first_txt[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        # Indices using offset:
        #   pollster = cells[1+offset]
        #   massa    = cells[4+offset]
        #   milei    = cells[5+offset]
        i_pollster = 1 + offset
        i_massa = 4 + offset
        i_milei = 5 + offset
        if i_milei >= len(cells) or i_pollster < 0:
            skipped.append(("short_row", str(len(cells))))
            continue
        pollster = _strip_html(cells[i_pollster])
        massa_pct = _pct(cells[i_massa])
        milei_pct = _pct(cells[i_milei])
        if massa_pct is None or milei_pct is None:
            skipped.append(("pct_missing", pollster))
            continue
        lead_milei = milei_pct - massa_pct
        datestr = d.isoformat()
        ctx_milei = (f"Javier Milei (LLA) vs Sergio Massa (UP) runoff "
                     f"in Argentina ({pollster}, {datestr})")
        ctx_massa = (f"Sergio Massa (UP) vs Javier Milei (LLA) runoff "
                     f"in Argentina ({pollster}, {datestr})")
        # Milei won 55.7%; Massa was incumbent finance minister of UP govt.
        out_rows.append({
            "evento_id": f"ar2023_{datestr}_{re.sub('[^a-z0-9]', '', pollster.lower())[:14]}_milei",
            "data": datestr,
            "contexto": ctx_milei,
            "uf": "AR",
            "ano": 2023,
            "turno": 2,
            "vencedor": "Javier Milei",
            "partido": "LLA",
            "incumbente": 0,
            "poll_lead_pp": round(lead_milei, 2),
            "outcome_real": 1,
            "probabilidade_prior": round(0.5 + lead_milei / 80.0, 3),
            "outcome_framing": ctx_milei,
        })
        out_rows.append({
            "evento_id": f"ar2023_{datestr}_{re.sub('[^a-z0-9]', '', pollster.lower())[:14]}_massa",
            "data": datestr,
            "contexto": ctx_massa,
            "uf": "AR",
            "ano": 2023,
            "turno": 2,
            "vencedor": "Javier Milei",
            "partido": "UP",
            "incumbente": 1,
            "poll_lead_pp": round(-lead_milei, 2),
            "outcome_real": 0,
            "probabilidade_prior": round(0.5 - lead_milei / 80.0, 3),
            "outcome_framing": ctx_massa,
        })
        n_used += 1

    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input,
        "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2023 Argentine general election (After the primaries)",
    }


# --------------------------------------------------- Brazil 2014 (runoff) ---

BR_2014_ELECTION = "2014-10-26"
BR_PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}


def _br_pt_date(s: str, year: int = 2014) -> date | None:
    """Parse '24 e 25 de outubro' or '25 de outubro' -> last day."""
    s = _strip_html(s).lower()
    s = s.replace("ç", "c").replace("ã", "a").replace("é", "e")
    # match all 'd ... de mes' patterns; take last
    matches = list(re.finditer(r"(\d{1,2})\s+(?:e|a|de)?\s*\d{0,2}\s*"
                               r"de\s+([a-z]+)", s))
    if matches:
        last = matches[-1]
        day = int(last.group(1))
        mon_name = last.group(2)
        if mon_name in BR_PT_MONTHS:
            try:
                return date(year, BR_PT_MONTHS[mon_name], day)
            except ValueError:
                return None
    # fallback: 'd de mes' alone
    m = re.search(r"(\d{1,2})\s+de\s+([a-z]+)", s)
    if m and m.group(2) in BR_PT_MONTHS:
        try:
            return date(year, BR_PT_MONTHS[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


def build_br_2014(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "BR 2014 HTML missing"}
    html = html_path.read_text()
    m = re.search(r'<h2 id="Segundo_turno">.*?(?=<h2\s)', html, flags=re.DOTALL)
    if not m:
        return {"status": "data_unavailable",
                "note": "Segundo_turno section not found"}
    section = m.group()
    tab_m = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                      section, flags=re.DOTALL)
    if not tab_m:
        return {"status": "data_unavailable", "note": "BR 2014 runoff table not found"}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tab_m.group(), flags=re.DOTALL)

    election_dt = date.fromisoformat(BR_2014_ELECTION)
    out_rows = []
    n_input = 0
    n_used = 0
    skipped = []
    for raw in rows[2:]:  # skip 2 header rows
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", raw, flags=re.DOTALL)
        if len(cells) < 7:
            continue
        n_input += 1
        # Layout per inspection:
        # cells[0] = rank (th); cells[1] = period; cells[2] = institute;
        # cells[3] = MoE; cells[4] = Dilma; cells[5] = Aecio; ...
        date_txt = _strip_html(cells[1])
        d = _br_pt_date(date_txt, 2014)
        if d is None:
            skipped.append(("date_unparsed", date_txt[:60]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        institute = _strip_html(cells[2])
        dilma_pct = _pct(cells[4])
        aecio_pct = _pct(cells[5])
        if dilma_pct is None or aecio_pct is None:
            skipped.append(("pct_missing", institute))
            continue
        lead = dilma_pct - aecio_pct
        datestr = d.isoformat()
        ctx_dilma = (f"Dilma Rousseff (PT) vs Aecio Neves (PSDB) "
                     f"runoff Brasil 2014 ({institute}, {datestr})")
        ctx_aecio = (f"Aecio Neves (PSDB) vs Dilma Rousseff (PT) "
                     f"runoff Brasil 2014 ({institute}, {datestr})")
        # Dilma won 51.6%. PT was incumbent.
        out_rows.append({
            "evento_id": f"br2014_{datestr}_{re.sub('[^a-z0-9]', '', institute.lower())[:14]}_dilma",
            "data": datestr,
            "contexto": ctx_dilma,
            "uf": "BR",
            "ano": 2014,
            "turno": 2,
            "vencedor": "Dilma Rousseff",
            "partido": "PT",
            "incumbente": 1,
            "poll_lead_pp": round(lead, 2),
            "outcome_real": 1,
            "probabilidade_prior": round(0.5 + lead / 80.0, 3),
            "outcome_framing": ctx_dilma,
        })
        out_rows.append({
            "evento_id": f"br2014_{datestr}_{re.sub('[^a-z0-9]', '', institute.lower())[:14]}_aecio",
            "data": datestr,
            "contexto": ctx_aecio,
            "uf": "BR",
            "ano": 2014,
            "turno": 2,
            "vencedor": "Dilma Rousseff",
            "partido": "PSDB",
            "incumbente": 0,
            "poll_lead_pp": round(-lead, 2),
            "outcome_real": 0,
            "probabilidade_prior": round(0.5 - lead / 80.0, 3),
            "outcome_framing": ctx_aecio,
        })
        n_used += 1

    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input,
        "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia (PT): Pesquisas de opiniao para a eleicao presidencial no Brasil em 2014 (Segundo turno)",
    }


# ----------------------------------------- US 2022 governor (538 polls) ---

# Top 10 swing/competitive 2022 governor races (by FiveThirtyEight rating).
US_2022_GOV_TARGETS = {
    "Arizona", "Georgia", "Wisconsin", "Michigan", "Pennsylvania",
    "Nevada", "Oregon", "Kansas", "Maine", "New Mexico",
}

US_STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# Ground truth: party of WINNER for 2022 governor races (state-by-state).
# Source: certified state results; widely public.
US_2022_GOV_WINNER = {
    "Arizona": ("Katie Hobbs", "DEM"),
    "Georgia": ("Brian Kemp", "REP"),
    "Wisconsin": ("Tony Evers", "DEM"),
    "Michigan": ("Gretchen Whitmer", "DEM"),
    "Pennsylvania": ("Josh Shapiro", "DEM"),
    "Nevada": ("Joe Lombardo", "REP"),
    "Oregon": ("Tina Kotek", "DEM"),
    "Kansas": ("Laura Kelly", "DEM"),
    "Maine": ("Janet Mills", "DEM"),
    "New Mexico": ("Michelle Lujan Grisham", "DEM"),
}

# Incumbent party at time of 2022 election (state governorship).
US_2022_GOV_INCUMBENT_PARTY = {
    "Arizona": "REP",       # Doug Ducey (R) term-limited
    "Georgia": "REP",       # Kemp (R) running for re-election
    "Wisconsin": "DEM",     # Evers (D) running
    "Michigan": "DEM",      # Whitmer (D) running
    "Pennsylvania": "DEM",  # Wolf (D) term-limited
    "Nevada": "DEM",        # Sisolak (D) running
    "Oregon": "DEM",        # Brown (D) term-limited
    "Kansas": "DEM",        # Kelly (D) running
    "Maine": "DEM",         # Mills (D) running
    "New Mexico": "DEM",    # Lujan Grisham (D) running
}

US_2022_ELECTION = "2022-11-08"


def _538_date(s: str) -> date | None:
    """538 dates are M/D/YY."""
    s = (s or "").strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def build_us_2022_midterms(in_csv: Path, out_csv: Path) -> dict:
    if not in_csv.exists():
        return {"status": "data_unavailable", "note": "538 governor CSV missing"}

    election_dt = date.fromisoformat(US_2022_ELECTION)
    by_question_party: dict[tuple[str, str], dict] = {}
    n_input = 0
    with in_csv.open(encoding="utf-8", errors="replace") as fh:
        r = csv.DictReader(fh)
        for row in r:
            if row.get("cycle") != "2022":
                continue
            if row.get("office_type") != "Governor":
                continue
            if row.get("stage") != "general":
                continue
            state = row.get("state", "").strip()
            if state not in US_2022_GOV_TARGETS:
                continue
            party = row.get("party", "").strip()
            if party not in {"DEM", "REP"}:
                continue
            d = _538_date(row.get("end_date", ""))
            if d is None:
                continue
            days_to = (election_dt - d).days
            if days_to < 0 or days_to > DAYS_FILTER:
                continue
            try:
                pct = float(row.get("pct") or "")
            except (ValueError, TypeError):
                continue
            n_input += 1
            qid = row.get("question_id", "")
            poll_id = row.get("poll_id", "")
            key = (poll_id, qid)
            entry = by_question_party.setdefault(key, {
                "state": state, "date": d, "pollster": row.get("pollster", ""),
                "parties": {},
            })
            # If multiple candidates of same party (primary leftover) take max
            if party not in entry["parties"] or pct > entry["parties"][party]["pct"]:
                entry["parties"][party] = {
                    "pct": pct,
                    "name": row.get("candidate_name", ""),
                }

    out_rows = []
    n_used = 0
    skipped = 0
    for (poll_id, qid), entry in by_question_party.items():
        if "DEM" not in entry["parties"] or "REP" not in entry["parties"]:
            skipped += 1
            continue
        state = entry["state"]
        d = entry["date"]
        datestr = d.isoformat()
        uf = US_STATE_ABBR[state]
        winner_name, winner_party = US_2022_GOV_WINNER[state]
        incumbent_party = US_2022_GOV_INCUMBENT_PARTY[state]
        dem_pct = entry["parties"]["DEM"]["pct"]
        rep_pct = entry["parties"]["REP"]["pct"]
        dem_name = entry["parties"]["DEM"]["name"]
        rep_name = entry["parties"]["REP"]["name"]
        pollster = entry["pollster"][:20]
        for party in ("DEM", "REP"):
            their = dem_pct if party == "DEM" else rep_pct
            other = rep_pct if party == "DEM" else dem_pct
            their_name = dem_name if party == "DEM" else rep_name
            other_name = rep_name if party == "DEM" else dem_name
            lead = their - other
            outcome = 1 if winner_party == party else 0
            incumbent = 1 if party == incumbent_party else 0
            ctx = (f"{their_name} ({party}) vs {other_name} for {state} "
                   f"governor 2022 ({pollster}, {datestr})")
            evento_id = (f"usgov2022_{datestr}_{uf}_"
                         f"{poll_id}_{qid}_{party.lower()}")
            out_rows.append({
                "evento_id": evento_id,
                "data": datestr,
                "contexto": ctx,
                "uf": uf,
                "ano": 2022,
                "turno": 1,
                "vencedor": winner_name,
                "partido": party,
                "incumbente": incumbent,
                "poll_lead_pp": round(lead, 2),
                "outcome_real": outcome,
                "probabilidade_prior": round(0.5 + lead / 80.0, 3),
                "outcome_framing": ctx,
            })
        n_used += 1

    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input,
        "n_question_pairs": n_used,
        "n_unmatched_pairs": skipped,
        "n_csv_rows": len(out_rows),
        "states_covered": sorted({US_STATE_ABBR[r["state"]]
                                  for r in by_question_party.values()
                                  if "DEM" in r["parties"] and "REP" in r["parties"]}),
        "source": "FiveThirtyEight governor_polls.csv (2022 cycle, via Wayback Machine)",
    }


# --------------------------------------------- evaluation: MRP vs no-MRP ---

# Regime taxonomy. For non-US/UK we map party -> {left, right, center}.
REGIME_BY_PARTY = {
    # FR
    "LREM": "center", "RN": "right",
    # AR
    "UP": "left", "LLA": "right", "JxC": "right",
    # BR
    "PT": "left", "PSDB": "right",
    # US
    "DEM": "dem", "REP": "rep",
}


def _row_to_event(r: dict, country: str, election_iso: str) -> dict:
    election_dt = date.fromisoformat(election_iso)
    poll_dt = date.fromisoformat(r["data"][:10])
    days = max(0, (election_dt - poll_dt).days)
    lead = float(r["poll_lead_pp"])
    partido = r["partido"]
    regime = REGIME_BY_PARTY.get(partido, "center")
    cargo = "presidente" if country in {"FR", "AR", "BR"} else "governador"
    return {
        "evento_id": r["evento_id"],
        "uf": r["uf"],
        "ano": int(r["ano"]),
        "data": r["data"],
        "outcome": int(r["outcome_real"]),
        "p_prior": float(r.get("probabilidade_prior", 0.5)),
        "cargo": cargo,
        "lead_bin": lead_bin(lead),
        "days_bin": days_bin(days),
        "incumbente": int(r.get("incumbente", 0)),
        "regime": regime,
        "context": r.get("outcome_framing", ""),
        "poll_lead_pp": lead,
        "days_to": days,
    }


def load_country_csv(path: Path, country: str, election_iso: str) -> list[dict]:
    if not path.exists():
        return []
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return [_row_to_event(r, country, election_iso) for r in rows]


def _lead_to_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLO * max(0, days)
    z = lead_pp / max(sigma, 1.0)
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def predict_one(e: dict, rates: dict, w_state: float) -> float:
    pred = predict_political(e, rates)
    p_coh = pred["p_raw"]
    p_lnz = _lead_to_p(e.get("poll_lead_pp", 0.0), e.get("days_to", 30))
    p = (1.0 - W_LINZER) * p_coh + W_LINZER * p_lnz
    if w_state > 0:
        p_state = state_baseline_p(rates, e.get("uf", ""), e["regime"])
        if p_state is not None:
            p = (1.0 - w_state) * p + w_state * p_state
    return float(p)


def evaluate(events: list[dict], rates: dict, w_state: float) -> dict:
    if not events:
        return {"n": 0}
    n = len(events)
    brier_sum = 0.0
    hits = 0
    by_uf: dict[str, list[int]] = defaultdict(list)
    for e in events:
        p = predict_one(e, rates, w_state)
        y = int(e["outcome"])
        brier_sum += (p - y) ** 2
        hit = int((p >= 0.5) == bool(y))
        hits += hit
        by_uf[e["uf"]].append(hit)
    return {
        "n": n,
        "brier": brier_sum / n,
        "acc": hits / n,
        "by_uf_acc": {u: round(sum(v) / len(v), 4) for u, v in by_uf.items()},
        "n_per_uf": {u: len(v) for u, v in by_uf.items()},
    }


def evaluate_country(events: list[dict]) -> dict:
    """LOSO across uf when there are >= 2 distinct ufs; otherwise fall back
    to leave-one-poll-out (per-pair LOOCV).
    For single-uf runoff cycles (FR/AR/BR) we run leave-one-pair-out:
    train cohort on all events except the two rows from one polldate, eval
    on those two rows."""
    out = {}
    if not events:
        return {"n": 0, "note": "no events"}

    # In-sample diagnostic
    rates_full = fit_cohorts_political(events, stein_shrink=STEIN_SHRINK)
    base_full = evaluate(events, rates_full, w_state=0.0)
    mrp_full = evaluate(events, rates_full, w_state=W_STATE)
    out["in_sample"] = {
        "no_mrp": {"acc": base_full["acc"], "brier": base_full["brier"], "n": base_full["n"]},
        "mrp_w36": {"acc": mrp_full["acc"], "brier": mrp_full["brier"], "n": mrp_full["n"]},
    }

    states = sorted({e["uf"] for e in events})
    if len(states) >= 2:
        # LOSO per state
        base_acc_sum = 0; base_brier_sum = 0; base_n = 0
        mrp_acc_sum = 0; mrp_brier_sum = 0; mrp_n = 0
        per_state = {}
        for s in states:
            train = [e for e in events if e["uf"] != s]
            test = [e for e in events if e["uf"] == s]
            if not train or not test:
                continue
            rates = fit_cohorts_political(train, stein_shrink=STEIN_SHRINK)
            base_e = evaluate(test, rates, w_state=0.0)
            mrp_e = evaluate(test, rates, w_state=W_STATE)
            per_state[s] = {
                "n": base_e["n"],
                "no_mrp_acc": round(base_e["acc"], 4),
                "mrp_acc": round(mrp_e["acc"], 4),
                "no_mrp_brier": round(base_e["brier"], 4),
                "mrp_brier": round(mrp_e["brier"], 4),
            }
            base_acc_sum += base_e["acc"] * base_e["n"]
            base_brier_sum += base_e["brier"] * base_e["n"]
            base_n += base_e["n"]
            mrp_acc_sum += mrp_e["acc"] * mrp_e["n"]
            mrp_brier_sum += mrp_e["brier"] * mrp_e["n"]
            mrp_n += mrp_e["n"]
        if base_n:
            out["loso"] = {
                "no_mrp": {"acc": base_acc_sum / base_n,
                           "brier": base_brier_sum / base_n,
                           "n": base_n},
                "mrp_w36": {"acc": mrp_acc_sum / mrp_n,
                            "brier": mrp_brier_sum / mrp_n,
                            "n": mrp_n},
                "per_state": per_state,
            }
    else:
        # Single-uf: leave-one-pair-out by date+pollster
        # group events by (data, evento_id_prefix)
        groups: dict[str, list[dict]] = defaultdict(list)
        for e in events:
            # group key = data (one pollster usually unique per date but
            # multiple pollsters share dates): use first 30 chars of evento_id
            key = e["evento_id"].rsplit("_", 1)[0]  # strip last token (winner/loser)
            groups[key].append(e)

        base_acc_sum = 0; base_brier_sum = 0; base_n = 0
        mrp_acc_sum = 0; mrp_brier_sum = 0; mrp_n = 0
        for k, test in groups.items():
            train = [e for e in events if e["evento_id"].rsplit("_", 1)[0] != k]
            if not train or not test:
                continue
            rates = fit_cohorts_political(train, stein_shrink=STEIN_SHRINK)
            base_e = evaluate(test, rates, w_state=0.0)
            mrp_e = evaluate(test, rates, w_state=W_STATE)
            base_acc_sum += base_e["acc"] * base_e["n"]
            base_brier_sum += base_e["brier"] * base_e["n"]
            base_n += base_e["n"]
            mrp_acc_sum += mrp_e["acc"] * mrp_e["n"]
            mrp_brier_sum += mrp_e["brier"] * mrp_e["n"]
            mrp_n += mrp_e["n"]
        if base_n:
            out["loso"] = {
                "_mode": "leave_one_pair_out (single-uf cycle)",
                "no_mrp": {"acc": base_acc_sum / base_n,
                           "brier": base_brier_sum / base_n,
                           "n": base_n},
                "mrp_w36": {"acc": mrp_acc_sum / mrp_n,
                            "brier": mrp_brier_sum / mrp_n,
                            "n": mrp_n},
            }
    out["n_states"] = len(states)
    return out


# ------------------------------------------------------------------ main ---


def main():
    print("=== Vila MRP cross-country EXTENDED validation (Phase 4) ===\n")

    fr_html = RAW_DIR / "wiki_fr_2022_polls.html"
    ar_html = RAW_DIR / "wiki_ar_2023_polls.html"
    br_html = RAW_DIR / "wiki_br_2014_polls.html"
    us_csv = RAW_DIR / "fte_governor_polls_2022.csv"

    out_fr = OUT_DIR / "fr_2022_president.csv"
    out_ar = OUT_DIR / "ar_2023_president.csv"
    out_br = OUT_DIR / "br_2014_president.csv"
    out_us = OUT_DIR / "us_2022_midterms.csv"

    fetch_status: dict = {}

    fetch_status["fr_2022"] = build_fr_2022(fr_html, out_fr)
    print(f"FR 2022: {fetch_status['fr_2022']}")

    fetch_status["ar_2023"] = build_ar_2023(ar_html, out_ar)
    print(f"AR 2023: {fetch_status['ar_2023']}")

    fetch_status["br_2014"] = build_br_2014(br_html, out_br)
    print(f"BR 2014: {fetch_status['br_2014']}")

    fetch_status["us_2022"] = build_us_2022_midterms(us_csv, out_us)
    print(f"US 2022: {fetch_status['us_2022']}")

    # ---- Apply Vila MRP per cycle ----
    print("\n=== Applying Vila MRP architecture per cycle ===\n")

    results: dict = {"_fetch": fetch_status}

    cycles = [
        ("fr_2022", out_fr, "FR", FR_ELECTION),
        ("ar_2023", out_ar, "AR", AR_ELECTION),
        ("br_2014", out_br, "BR", BR_2014_ELECTION),
        ("us_2022", out_us, "US", US_2022_ELECTION),
    ]
    accs = []; briers = []; weights = []
    no_mrp_accs = []; no_mrp_briers = []
    for label, csv_path, country, election_iso in cycles:
        events = load_country_csv(csv_path, country, election_iso)
        print(f"-- {label}: {len(events)} events from {csv_path.name}")
        if not events:
            results[label] = {"n": 0, "status": "no events parsed",
                              "data_path": str(csv_path.relative_to(ROOT))}
            continue
        evald = evaluate_country(events)
        evald["n_events"] = len(events)
        evald["data_path"] = str(csv_path.relative_to(ROOT))
        results[label] = evald
        if "loso" in evald:
            print(f"   LOSO no-MRP: acc={evald['loso']['no_mrp']['acc']:.4f}  "
                  f"brier={evald['loso']['no_mrp']['brier']:.4f}  "
                  f"n={evald['loso']['no_mrp']['n']}")
            print(f"   LOSO MRP w=0.36: acc={evald['loso']['mrp_w36']['acc']:.4f}  "
                  f"brier={evald['loso']['mrp_w36']['brier']:.4f}  "
                  f"n={evald['loso']['mrp_w36']['n']}")
            accs.append(evald['loso']['mrp_w36']['acc'])
            briers.append(evald['loso']['mrp_w36']['brier'])
            no_mrp_accs.append(evald['loso']['no_mrp']['acc'])
            no_mrp_briers.append(evald['loso']['no_mrp']['brier'])
            weights.append(evald['loso']['mrp_w36']['n'])

    if accs:
        wsum = sum(weights)
        results["avg_extended"] = {
            "acc_unweighted": sum(accs) / len(accs),
            "acc_weighted": sum(a * w for a, w in zip(accs, weights)) / wsum,
            "brier_unweighted": sum(briers) / len(briers),
            "brier_weighted": sum(b * w for b, w in zip(briers, weights)) / wsum,
            "no_mrp_acc_unweighted": sum(no_mrp_accs) / len(no_mrp_accs),
            "no_mrp_brier_unweighted": sum(no_mrp_briers) / len(no_mrp_briers),
            "n_total": wsum,
            "cycles_with_loso": len(accs),
        }
    else:
        results["avg_extended"] = {"note": "no usable LOSO results"}

    RESULT_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved -> {RESULT_PATH.relative_to(ROOT)}")

    print("\n=== SUMMARY ===")
    for label, _, _, _ in cycles:
        v = results.get(label, {})
        loso = v.get("loso") if isinstance(v, dict) else None
        if loso:
            d = loso['mrp_w36']['acc'] - loso['no_mrp']['acc']
            print(f"  {label:<8} n={v.get('n_events')}  "
                  f"no-MRP acc={loso['no_mrp']['acc']:.4f}  "
                  f"MRP acc={loso['mrp_w36']['acc']:.4f}  "
                  f"delta={d:+.4f}")
        else:
            status = v.get("status") if isinstance(v, dict) else "unknown"
            print(f"  {label}: no LOSO ({status})")
    avg = results.get("avg_extended", {})
    if "acc_weighted" in avg:
        print(f"  avg_extended (weighted): MRP acc={avg['acc_weighted']:.4f}  "
              f"no-MRP acc={avg.get('no_mrp_acc_unweighted', 'NA'):.4f}  "
              f"n={avg['n_total']}")


if __name__ == "__main__":
    main()
