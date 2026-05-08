#!/usr/bin/env python3
"""Phase 5: Cross-country generalization extended to 5 NEW electoral cycles.

Adds to scripts/cross_country_extended.py:
  - Germany 2021 Bundestag (Scholz/SPD vs Laschet/CDU/CSU; SPD recovery)
  - Mexico 2024 presidential (Sheinbaum landslide; baseline easy case)
  - Turkey 2023 presidential runoff (Erdogan vs Kilicdaroglu)
  - Italy 2022 general (Centre-right Meloni; coalition vote)
  - India 2024 Lok Sabha (NDA over INDIA in vote share; exit-poll fail on seats)

Data sources (raw HTML under data/cross_country/raw_more/):
  - Wikipedia: "Opinion polling for the 2021 German federal election"
  - Wikipedia: "Opinion polling for the 2024 Mexican general election"
  - Wikipedia: "Opinion polling for the 2023 Turkish presidential election"
  - Wikipedia: "Opinion polling for the 2022 Italian general election"
  - Wikipedia: "Opinion polling for the 2024 Indian general election"

Pipeline per cycle (same protocol as cross_country_extended.py):
  1. Parse poll-level rows, build paired (winner=1, loser=0) CSV in
     data/backtest/{cycle}.csv with the legacy schema.
  2. Filter T <= 30 days from election.
  3. Year-fold or leave-one-pair-out leak-safe CV; no_mrp vs mrp_w36.

If a source is absent or fails to parse, the cycle is marked
status="data_unavailable" and skipped, never synthesised.

Output:
  data/backtest/de_2021.csv
  data/backtest/mx_2024.csv
  data/backtest/tr_2023.csv
  data/backtest/it_2022.csv
  data/backtest/in_2024.csv
  data/cross_country_more.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import date
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

RAW_DIR = ROOT / "data" / "cross_country" / "raw_more"
OUT_DIR = ROOT / "data" / "backtest"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = ROOT / "data" / "cross_country_more.json"

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

# Election dates
DE_ELECTION = "2021-09-26"
MX_ELECTION = "2024-06-02"
TR_ELECTION = "2023-05-28"  # runoff
IT_ELECTION = "2022-09-25"
IN_ELECTION = "2024-06-01"  # last polling day; full count released 4 Jun

EN_MONTHS = {
    "Jan": 1, "January": 1, "Feb": 2, "February": 2, "Mar": 3, "March": 3,
    "Apr": 4, "April": 4, "May": 5, "Jun": 6, "June": 6, "Jul": 7, "July": 7,
    "Aug": 8, "August": 8, "Sep": 9, "Sept": 9, "September": 9, "Oct": 10,
    "October": 10, "Nov": 11, "November": 11, "Dec": 12, "December": 12,
}


# ------------------------------------------------------------------ helpers ---


def _strip_html(s: str) -> str:
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&#160;", " ")
    s = s.replace("&#91;", "[").replace("&#93;", "]")
    s = re.sub(r"\[[^\]]*\]", " ", s)  # strip [N] reference markers
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _pct(s: str) -> float | None:
    s = _strip_html(s)
    s = s.replace("%", "").replace(",", ".").strip()
    s = re.sub(r"\([^)]*\)", "", s).strip()
    if not s or s in {"-", "--", "?", "N/A"}:
        return None
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _data_sort_value_date(html_cell: str) -> date | None:
    """Wiki tables embed data-sort-value="YYYY-MM-DD" on date <td>; preferred."""
    m = re.search(r'data-sort-value="(\d{4})-(\d{1,2})-(\d{1,2})"', html_cell)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _en_date(s: str, default_year: int) -> date | None:
    """Parse 'd Mon YYYY' / 'd-d Mon YYYY' / 'd Mon - d Mon YYYY' / '21-22 Apr 2022' -> last day.
    Falls back to default_year if year not present."""
    s = _strip_html(s)
    # Format: 'd Mon - d Mon YYYY' (e.g., '28 May - 1 Jun 2024')
    m = re.search(r"\d{1,2}\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", s)
    if m:
        d_str = m.group(2)
        mon_str = m.group(3)
        yr = m.group(4)
        mon = EN_MONTHS.get(mon_str) or EN_MONTHS.get(mon_str[:3])
        year = int(yr) if yr else default_year
        if mon:
            try:
                return date(year, mon, int(d_str))
            except ValueError:
                pass
    # Format: 'd-d Mon YYYY' or 'd to d Mon YYYY'
    m2 = re.search(r"\d{1,2}\s*(?:-|to)\s*(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", s)
    if m2:
        d_str = m2.group(1)
        mon_str = m2.group(2)
        yr = m2.group(3)
        mon = EN_MONTHS.get(mon_str) or EN_MONTHS.get(mon_str[:3])
        year = int(yr) if yr else default_year
        if mon:
            try:
                return date(year, mon, int(d_str))
            except ValueError:
                pass
    # Format: 'd Mon YYYY' or 'd Mon'
    m3 = re.search(r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", s)
    if m3:
        d_str = m3.group(1)
        mon_str = m3.group(2)
        yr = m3.group(3)
        mon = EN_MONTHS.get(mon_str) or EN_MONTHS.get(mon_str[:3])
        year = int(yr) if yr else default_year
        if mon:
            try:
                return date(year, mon, int(d_str))
            except ValueError:
                pass
    # Format: 'Month YYYY' (e.g., 'April 2024')
    m4 = re.search(r"([A-Za-z]+)\s+(\d{4})", s)
    if m4:
        mon_str = m4.group(1)
        yr = m4.group(2)
        mon = EN_MONTHS.get(mon_str) or EN_MONTHS.get(mon_str[:3])
        if mon:
            try:
                return date(int(yr), mon, 15)  # midpoint of month
            except ValueError:
                pass
    return None


def _section(html: str, start_id: str, end_id: str | None = None) -> str:
    """Return slice from id=start_id to next h2/h3 (or to end_id if given)."""
    idx = html.find(f'id="{start_id}"')
    if idx < 0:
        return ""
    if end_id:
        end = html.find(f'id="{end_id}"', idx + 1)
        if end < 0:
            end = len(html)
    else:
        # next h2 or h3
        m = re.search(r'<h[23]\s', html[idx + 1:])
        end = idx + 1 + m.start() if m else len(html)
    return html[idx:end]


def _wiki_tables(section_html: str) -> list[str]:
    return re.findall(
        r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>.*?</table>',
        section_html, flags=re.DOTALL,
    )


def _table_rows(tab: str) -> list[str]:
    return re.findall(r"<tr[^>]*>(.*?)</tr>", tab, flags=re.DOTALL)


def _row_cells(raw_row: str) -> list[str]:
    return re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", raw_row, flags=re.DOTALL)


def _emit_pair(out_rows: list, *, key_prefix: str, datestr: str, pollster: str,
               uf: str, ano: int, turno: int,
               winner_name: str, winner_party: str, winner_incumbent: int,
               loser_name: str, loser_party: str, loser_incumbent: int,
               winner_pct: float, loser_pct: float, country_label: str):
    """Emit two paired (winner=1, loser=0) rows with the legacy schema."""
    lead = winner_pct - loser_pct
    pollster_slug = re.sub("[^a-z0-9]", "", pollster.lower())[:14] or "p"
    ctx_w = (f"{winner_name} ({winner_party}) vs {loser_name} ({loser_party}) "
             f"in {country_label} ({pollster}, {datestr})")
    ctx_l = (f"{loser_name} ({loser_party}) vs {winner_name} ({winner_party}) "
             f"in {country_label} ({pollster}, {datestr})")
    out_rows.append({
        "evento_id": f"{key_prefix}_{datestr}_{pollster_slug}_w",
        "data": datestr,
        "contexto": ctx_w,
        "uf": uf,
        "ano": ano,
        "turno": turno,
        "vencedor": winner_name,
        "partido": winner_party,
        "incumbente": winner_incumbent,
        "poll_lead_pp": round(lead, 2),
        "outcome_real": 1,
        "probabilidade_prior": round(0.5 + lead / 80.0, 3),
        "outcome_framing": ctx_w,
    })
    out_rows.append({
        "evento_id": f"{key_prefix}_{datestr}_{pollster_slug}_l",
        "data": datestr,
        "contexto": ctx_l,
        "uf": uf,
        "ano": ano,
        "turno": turno,
        "vencedor": winner_name,
        "partido": loser_party,
        "incumbente": loser_incumbent,
        "poll_lead_pp": round(-lead, 2),
        "outcome_real": 0,
        "probabilidade_prior": round(0.5 - lead / 80.0, 3),
        "outcome_framing": ctx_l,
    })


def _write_csv(out_csv: Path, out_rows: list[dict]):
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)


# ----------------------------------------- Germany 2021 (Bundestag) ---


def build_de_2021(html_path: Path, out_csv: Path) -> dict:
    """Parse 2021 federal-election polling table (head-to-head SPD vs CDU/CSU
    extracted from the multi-party Sonntagsfrage table)."""
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "DE HTML missing"}
    html = html_path.read_text()
    section = _section(html, "2021", end_id="2020")  # 2021 sub-section, then 2020 starts
    if not section:
        return {"status": "data_unavailable", "note": "DE 2021 section not found"}
    tabs = _wiki_tables(section)
    if not tabs:
        return {"status": "data_unavailable", "note": "DE 2021 no tables"}
    rows = _table_rows(tabs[0])
    election_dt = date.fromisoformat(DE_ELECTION)
    out_rows = []
    n_input = 0; n_used = 0; skipped: list = []

    # Layout: [pollster, date, sample, abs, Union, SPD, AfD, FDP, Linke, Grune, FW, Others, Lead]
    # Skip first 2 header rows (rowspan=2 + party-color row).
    for raw in rows[2:]:
        cells = _row_cells(raw)
        if len(cells) < 7:
            continue
        n_input += 1
        pollster = _strip_html(cells[0])
        if not pollster or "election" in pollster.lower() or "result" in pollster.lower():
            continue
        d = _data_sort_value_date(cells[1]) or _en_date(_strip_html(cells[1]), 2021)
        if d is None:
            skipped.append(("date_unparsed", _strip_html(cells[1])[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        union_pct = _pct(cells[4])
        spd_pct = _pct(cells[5])
        if union_pct is None or spd_pct is None:
            skipped.append(("pct_missing", pollster))
            continue
        # SPD won (Scholz, 25.7%) vs CDU/CSU (Laschet, 24.1%). Merkel (CDU)
        # incumbent chancellor; Laschet runs as sitting governing-coalition party.
        # SPD was junior partner in Merkel grand coalition -> incumbent=1 too.
        # We treat *governing-party* as incumbent for both.
        datestr = d.isoformat()
        _emit_pair(
            out_rows,
            key_prefix="de2021", datestr=datestr, pollster=pollster,
            uf="DE", ano=2021, turno=1,
            winner_name="Olaf Scholz", winner_party="SPD", winner_incumbent=1,
            loser_name="Armin Laschet", loser_party="CDU/CSU", loser_incumbent=1,
            winner_pct=spd_pct, loser_pct=union_pct,
            country_label="2021 German federal election",
        )
        n_used += 1

    _write_csv(out_csv, out_rows)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input, "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2021 German federal election (2021 sub-section)",
    }


# ----------------------------------------- Mexico 2024 (presidential) ---


def build_mx_2024(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "MX HTML missing"}
    html = html_path.read_text()
    section = _section(html, "Campaigning_period")
    if not section:
        return {"status": "data_unavailable", "note": "MX Campaigning_period not found"}
    tabs = _wiki_tables(section)
    if not tabs:
        return {"status": "data_unavailable", "note": "MX no tables"}
    rows = _table_rows(tabs[0])
    election_dt = date.fromisoformat(MX_ELECTION)
    out_rows = []
    n_input = 0; n_used = 0; skipped: list = []
    # Layout: [date, pollster, sample, Sheinbaum, Galvez, Maynez, Others, Lead]
    for raw in rows[2:]:  # skip 2 header rows
        cells = _row_cells(raw)
        if len(cells) < 6:
            continue
        n_input += 1
        first = _strip_html(cells[0])
        if "election" in first.lower() or "result" in first.lower():
            continue
        d = _data_sort_value_date(cells[0]) or _en_date(first, 2024)
        if d is None:
            skipped.append(("date_unparsed", first[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        pollster = _strip_html(cells[1])
        sheinbaum = _pct(cells[3])
        galvez = _pct(cells[4])
        if sheinbaum is None or galvez is None:
            skipped.append(("pct_missing", pollster))
            continue
        datestr = d.isoformat()
        # Sheinbaum (Morena/SHH) won 60% over Galvez (PAN/PRI/PRD = FCM) 27%.
        # Sheinbaum is incumbent-party (Morena governs with AMLO).
        _emit_pair(
            out_rows,
            key_prefix="mx2024", datestr=datestr, pollster=pollster,
            uf="MX", ano=2024, turno=1,
            winner_name="Claudia Sheinbaum", winner_party="MORENA",
            winner_incumbent=1,
            loser_name="Xochitl Galvez", loser_party="FCM",
            loser_incumbent=0,
            winner_pct=sheinbaum, loser_pct=galvez,
            country_label="2024 Mexican presidential election",
        )
        n_used += 1
    _write_csv(out_csv, out_rows)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input, "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2024 Mexican general election (Campaigning period)",
    }


# ----------------------------------------- Turkey 2023 (runoff) ---


def build_tr_2023(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "TR HTML missing"}
    html = html_path.read_text()
    # Section "Second_round" up to "Notes"
    idx = html.find('id="Second_round"')
    end = html.find('id="Notes"', idx + 1)
    if idx < 0:
        return {"status": "data_unavailable", "note": "TR Second_round not found"}
    section = html[idx:end if end > 0 else len(html)]
    tabs = _wiki_tables(section)
    if len(tabs) < 2:
        return {"status": "data_unavailable", "note": "TR insufficient tables"}
    # Use the official-campaign table (table[1]): pre-runoff polls 14-28 May 2023.
    rows = _table_rows(tabs[1])
    election_dt = date.fromisoformat(TR_ELECTION)
    out_rows = []
    n_input = 0; n_used = 0; skipped: list = []
    # Layout: [date, pollster, sample, Erdogan, Kilicdaroglu, Lead]
    for raw in rows[3:]:  # skip 3 header rows (rowspan + names + colour)
        cells = _row_cells(raw)
        if len(cells) < 5:
            continue
        n_input += 1
        first = _strip_html(cells[0])
        if "election" in first.lower() or "result" in first.lower() or "runoff" in first.lower():
            continue
        d = _data_sort_value_date(cells[0]) or _en_date(first, 2023)
        if d is None:
            skipped.append(("date_unparsed", first[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        pollster = _strip_html(cells[1])
        erd = _pct(cells[3])
        kk = _pct(cells[4])
        if erd is None or kk is None:
            skipped.append(("pct_missing", pollster))
            continue
        datestr = d.isoformat()
        # Erdogan (AKP/PEOPLE) won 52.18% vs Kilicdaroglu (CHP/NATION) 47.82%.
        # Erdogan is incumbent president since 2014.
        _emit_pair(
            out_rows,
            key_prefix="tr2023", datestr=datestr, pollster=pollster,
            uf="TR", ano=2023, turno=2,
            winner_name="Recep Tayyip Erdogan", winner_party="AKP",
            winner_incumbent=1,
            loser_name="Kemal Kilicdaroglu", loser_party="CHP",
            loser_incumbent=0,
            winner_pct=erd, loser_pct=kk,
            country_label="2023 Turkish presidential runoff",
        )
        n_used += 1
    _write_csv(out_csv, out_rows)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input, "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2023 Turkish presidential election (Second round, official campaign)",
    }


# ----------------------------------------- Italy 2022 (general) ---


def build_it_2022(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "IT HTML missing"}
    html = html_path.read_text()
    # Section "Coalition_vote" then "2022_2" sub-section
    section = _section(html, "Coalition_vote", end_id="Seat_projections")
    if not section:
        return {"status": "data_unavailable", "note": "IT Coalition_vote not found"}
    tabs = _wiki_tables(section)
    if not tabs:
        return {"status": "data_unavailable", "note": "IT no coalition tables"}
    rows = _table_rows(tabs[0])
    election_dt = date.fromisoformat(IT_ELECTION)
    out_rows = []
    n_input = 0; n_used = 0; skipped: list = []
    # Layout: [date, pollster, sample, Centre-right, M5S, Centre-left, A-IV, Others, Lead]
    for raw in rows[2:]:  # skip 2 header rows
        cells = _row_cells(raw)
        if len(cells) < 7:
            continue
        n_input += 1
        first = _strip_html(cells[0])
        if "election" in first.lower() or "result" in first.lower():
            continue
        d = _data_sort_value_date(cells[0]) or _en_date(first, 2022)
        if d is None:
            skipped.append(("date_unparsed", first[:50]))
            continue
        days_to = (election_dt - d).days
        if days_to < 0 or days_to > DAYS_FILTER:
            continue
        pollster = _strip_html(cells[1])
        cr_pct = _pct(cells[3])  # Centre-right (Meloni FdI/Lega/FI)
        cl_pct = _pct(cells[5])  # Centre-left (PD-led)
        if cr_pct is None or cl_pct is None:
            skipped.append(("pct_missing", pollster))
            continue
        datestr = d.isoformat()
        # Centre-right won 43.8% (Meloni FdI led) vs Centre-left 26.1%.
        # Draghi (technocrat) was outgoing PM; outcome was government change.
        # We treat Meloni's coalition as not-incumbent.
        _emit_pair(
            out_rows,
            key_prefix="it2022", datestr=datestr, pollster=pollster,
            uf="IT", ano=2022, turno=1,
            winner_name="Giorgia Meloni", winner_party="CDX",
            winner_incumbent=0,
            loser_name="Enrico Letta", loser_party="CSX",
            loser_incumbent=0,
            winner_pct=cr_pct, loser_pct=cl_pct,
            country_label="2022 Italian general election (coalition vote)",
        )
        n_used += 1
    _write_csv(out_csv, out_rows)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input, "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2022 Italian general election (Coalition vote)",
    }


# ----------------------------------------- India 2024 (Lok Sabha) ---


def build_in_2024(html_path: Path, out_csv: Path) -> dict:
    if not html_path.exists():
        return {"status": "data_unavailable", "note": "IN HTML missing"}
    html = html_path.read_text()
    # Section "Seats_and_vote_share_projections"; first table = vote share.
    section = _section(html, "Seats_and_vote_share_projections",
                       end_id="Data_of_states_and_union_territories")
    if not section:
        return {"status": "data_unavailable",
                "note": "IN Seats_and_vote_share_projections not found"}
    tabs = _wiki_tables(section)
    if not tabs:
        return {"status": "data_unavailable", "note": "IN no projection tables"}
    rows = _table_rows(tabs[0])
    election_dt = date.fromisoformat(IN_ELECTION)
    out_rows = []
    n_input = 0; n_used = 0; skipped: list = []
    # Layout: [pollster, date_published, sample, MoE, NDA, INDIA, Others, Lead]
    # Skip 2 header rows (rowspan+alliance row).
    for raw in rows[2:]:
        cells = _row_cells(raw)
        if len(cells) < 6:
            continue
        n_input += 1
        first = _strip_html(cells[0])
        if "election" in first.lower() or "result" in first.lower():
            continue
        # Date is in cells[1]
        date_txt = _strip_html(cells[1])
        d = _data_sort_value_date(cells[1]) or _en_date(date_txt, 2024)
        if d is None:
            skipped.append(("date_unparsed", date_txt[:60]))
            continue
        days_to = (election_dt - d).days
        # IN polls are coarser (published monthly, not by fieldwork date);
        # widen filter to 120 days to capture Feb-May 2024 horizon.
        if days_to < 0 or days_to > 120:
            continue
        pollster = first
        nda_pct = _pct(cells[4])
        india_pct = _pct(cells[5])
        if nda_pct is None or india_pct is None:
            skipped.append(("pct_missing", pollster))
            continue
        datestr = d.isoformat()
        # NDA (BJP-led) won 43.8% vs INDIA (Congress+) 41.48%. NDA is incumbent
        # (Modi BJP since 2014). Margin much smaller than polls projected
        # (most polls had NDA at 46-50%, INDIA 32-39%).
        _emit_pair(
            out_rows,
            key_prefix="in2024", datestr=datestr, pollster=pollster,
            uf="IN", ano=2024, turno=1,
            winner_name="Narendra Modi (NDA)", winner_party="NDA",
            winner_incumbent=1,
            loser_name="INDIA bloc", loser_party="INDIA",
            loser_incumbent=0,
            winner_pct=nda_pct, loser_pct=india_pct,
            country_label="2024 Indian Lok Sabha (vote share, NDA vs INDIA)",
        )
        n_used += 1
    _write_csv(out_csv, out_rows)
    return {
        "status": "ok" if out_rows else "data_unavailable",
        "n_input_rows": n_input, "n_polls_used": n_used,
        "n_csv_rows": len(out_rows),
        "days_filter_used": 120,
        "skipped_examples": skipped[:5],
        "source": "Wikipedia: Opinion polling for the 2024 Indian general election (vote-share projections)",
    }


# --------------------------------------------- evaluation: MRP vs no-MRP ---

REGIME_BY_PARTY = {
    # FR
    "LREM": "center", "RN": "right",
    # AR
    "UP": "left", "LLA": "right", "JxC": "right",
    # BR
    "PT": "left", "PSDB": "right",
    # US
    "DEM": "dem", "REP": "rep",
    # DE 2021
    "SPD": "left", "CDU/CSU": "center",
    # MX 2024
    "MORENA": "left", "FCM": "right",
    # TR 2023
    "AKP": "right", "CHP": "left",
    # IT 2022
    "CDX": "right", "CSX": "left",
    # IN 2024
    "NDA": "right", "INDIA": "center",
}


def _row_to_event(r: dict, country: str, election_iso: str) -> dict:
    election_dt = date.fromisoformat(election_iso)
    poll_dt = date.fromisoformat(r["data"][:10])
    days = max(0, (election_dt - poll_dt).days)
    lead = float(r["poll_lead_pp"])
    partido = r["partido"]
    regime = REGIME_BY_PARTY.get(partido, "center")
    cargo = "presidente"  # all 5 are presidential/national in nature
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
    for e in events:
        p = predict_one(e, rates, w_state)
        y = int(e["outcome"])
        brier_sum += (p - y) ** 2
        hits += int((p >= 0.5) == bool(y))
    return {"n": n, "brier": brier_sum / n, "acc": hits / n}


def evaluate_country(events: list[dict]) -> dict:
    """Single-uf cycles -> leave-one-pair-out by date+pollster."""
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

    # leave-one-pair-out by evento_id prefix (drop final winner/loser token).
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        key = e["evento_id"].rsplit("_", 1)[0]
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
                       "brier": base_brier_sum / base_n, "n": base_n},
            "mrp_w36": {"acc": mrp_acc_sum / mrp_n,
                        "brier": mrp_brier_sum / mrp_n, "n": mrp_n},
        }
    out["n_states"] = 1
    return out


# ------------------------------------------------------------------ main ---


def main():
    print("=== Vila MRP cross-country MORE validation (Phase 5) ===\n")

    out_de = OUT_DIR / "de_2021.csv"
    out_mx = OUT_DIR / "mx_2024.csv"
    out_tr = OUT_DIR / "tr_2023.csv"
    out_it = OUT_DIR / "it_2022.csv"
    out_in = OUT_DIR / "in_2024.csv"

    fetch_status: dict = {}
    fetch_status["de_2021"] = build_de_2021(RAW_DIR / "wiki_de_2021_polls.html", out_de)
    print(f"DE 2021: {fetch_status['de_2021']}")
    fetch_status["mx_2024"] = build_mx_2024(RAW_DIR / "wiki_mx_2024_polls.html", out_mx)
    print(f"MX 2024: {fetch_status['mx_2024']}")
    fetch_status["tr_2023"] = build_tr_2023(RAW_DIR / "wiki_tr_2023_polls.html", out_tr)
    print(f"TR 2023: {fetch_status['tr_2023']}")
    fetch_status["it_2022"] = build_it_2022(RAW_DIR / "wiki_it_2022_polls.html", out_it)
    print(f"IT 2022: {fetch_status['it_2022']}")
    fetch_status["in_2024"] = build_in_2024(RAW_DIR / "wiki_in_2024_polls.html", out_in)
    print(f"IN 2024: {fetch_status['in_2024']}")

    print("\n=== Applying Vila MRP architecture per cycle ===\n")
    results: dict = {"_fetch": fetch_status}
    cycles = [
        ("de_2021", out_de, "DE", DE_ELECTION),
        ("mx_2024", out_mx, "MX", MX_ELECTION),
        ("tr_2023", out_tr, "TR", TR_ELECTION),
        ("it_2022", out_it, "IT", IT_ELECTION),
        ("in_2024", out_in, "IN", IN_ELECTION),
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
        results["avg_more"] = {
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
        results["avg_more"] = {"note": "no usable LOSO results"}

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
    avg = results.get("avg_more", {})
    if "acc_weighted" in avg:
        print(f"  avg_more (weighted): MRP acc={avg['acc_weighted']:.4f}  "
              f"no-MRP acc={avg.get('no_mrp_acc_unweighted', 'NA'):.4f}  "
              f"n={avg['n_total']}")


if __name__ == "__main__":
    main()
