"""
Parses a Word (.docx) file with annual target agreements and writes data/kpis.json.

Expected table format (one table per member, or one combined table):
  Column 0: Mitarbeiter (member name)
  Column 1: Rolle (role) - optional
  Column 2: KPI-Bezeichnung (goal title)
  Column 3: Startdatum (DD.MM.YYYY or YYYY-MM-DD)
  Column 4: Enddatum
  Column 5: Meilenstein (description)
  Column 6: Meilenstein-Datum

Rows with the same Mitarbeiter+KPI share milestones (one row per milestone).
"""

import json
import os
import re
import sys
from datetime import datetime, date

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "kpis.json")


def parse_date(raw):
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse(path):
    from docx import Document
    doc = Document(path)

    members_map = {}   # name -> member dict
    member_order = []

    def get_or_create_member(name, role=""):
        if name not in members_map:
            mid = "member_" + slugify(name)
            members_map[name] = {
                "id": mid,
                "name": name,
                "role": role or "",
                "kpis": []
            }
            member_order.append(name)
        elif role and not members_map[name]["role"]:
            members_map[name]["role"] = role
        return members_map[name]

    def get_or_create_kpi(member, goal_title, start_date, end_date):
        for kpi in member["kpis"]:
            if kpi["original_goal"] == goal_title:
                return kpi
        kid = member["id"] + "_kpi_" + str(len(member["kpis"]) + 1)
        kpi = {
            "id": kid,
            "original_goal": goal_title,
            "kpi_typ": "Sonstiges",
            "ebene": "Bund",
            "start_date": start_date,
            "end_date": end_date,
            "progress_percent": 0,
            "rag_status": "red",
            "milestones": [],
            "notes": ""
        }
        member["kpis"].append(kpi)
        return kpi

    def recalc_progress(kpi):
        ms = kpi.get("milestones", [])
        pct = round((sum(1 for m in ms if m["status"] == "completed") / len(ms)) * 100) if ms else 0
        kpi["progress_percent"] = pct
        today = date.today()
        start_str = kpi.get("start_date")
        end_str = kpi.get("end_date")
        try:
            if start_str and end_str:
                start = date.fromisoformat(start_str)
                end = date.fromisoformat(end_str)
                total_days = (end - start).days
                if total_days > 0:
                    elapsed = max(0, (today - start).days)
                    expected = min(100, round((elapsed / total_days) * 100))
                    delta = pct - expected
                    kpi["rag_status"] = "green" if delta >= -15 else "amber" if delta >= -40 else "red"
                    return
        except ValueError:
            pass
        kpi["rag_status"] = "green" if pct >= 75 else "amber" if pct >= 40 else "red"

    for table in doc.tables:
        rows = [
            [cell.text.strip() for cell in row.cells]
            for row in table.rows
        ]
        if not rows:
            continue

        # Skip header row
        header = rows[0]
        start_idx = 1 if any(h.lower() in ("mitarbeiter", "name", "kpi", "ziel") for h in header) else 0

        current_member = ""
        current_goal = ""
        current_typ = "Sonstiges"
        current_ebene = "Bund"
        current_start = ""
        current_end = ""

        for row in rows[start_idx:]:
            if len(row) < 2:
                continue

            # Expected columns: Mitarbeiter | KPI | KPI Typ | Ebene | Start | Ende | Meilenstein
            col_member = row[0] if len(row) > 0 else ""
            col_goal   = row[1] if len(row) > 1 else ""
            col_typ    = row[2] if len(row) > 2 else ""
            col_ebene  = row[3] if len(row) > 3 else ""
            col_start  = row[4] if len(row) > 4 else ""
            col_end    = row[5] if len(row) > 5 else ""
            col_ms     = row[6] if len(row) > 6 else ""

            if col_member:
                current_member = col_member
            if col_goal:
                current_goal = col_goal
            if col_typ:
                current_typ = col_typ
            if col_ebene:
                current_ebene = col_ebene
            if col_start:
                current_start = parse_date(col_start)
            if col_end:
                current_end = parse_date(col_end)

            if not current_member or not current_goal:
                continue

            member = get_or_create_member(current_member)
            kpi = get_or_create_kpi(member, current_goal, current_start, current_end)
            kpi["kpi_typ"] = current_typ
            kpi["ebene"] = current_ebene

            if col_ms:
                kpi["milestones"].append({
                    "description": col_ms,
                    "status": "open"
                })

    for name in member_order:
        for kpi in members_map[name]["kpis"]:
            recalc_progress(kpi)

    existing = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
            existing["generated_at"] = old.get("generated_at", "")
            existing["year"] = old.get("year", date.today().year)
            existing["team_name"] = old.get("team_name", "Mein Team")
    except Exception:
        existing = {"year": date.today().year, "team_name": "Mein Team"}

    output = {
        "generated_at": date.today().isoformat(),
        "year": existing.get("year", date.today().year),
        "team_name": existing.get("team_name", "Mein Team"),
        "members": [members_map[n] for n in member_order]
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Fertig: {len(member_order)} Mitglieder eingelesen → {DATA_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Verwendung: python3 parse_goals.py pfad/zur/datei.docx")
        sys.exit(1)
    parse(sys.argv[1])
