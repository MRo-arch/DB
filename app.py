from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import os
from datetime import date, timedelta

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "kpis.json")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


DEFAULT_DATA = {
    "generated_at": date.today().isoformat(),
    "year": date.today().year,
    "team_name": "Mein Team",
    "members": []
}


def load_data():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        save_data(DEFAULT_DATA)
        return dict(DEFAULT_DATA)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    changed = False
    for member in data.get("members", []):
        for kpi in member.get("kpis", []):
            new_rag = compute_rag(kpi.get("progress_percent", 0), kpi.get("start_date"), kpi.get("end_date"))
            if new_rag != kpi.get("rag_status"):
                kpi["rag_status"] = new_rag
                changed = True
    if changed:
        save_data(data)
    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_rag(progress, start_date=None, end_date=None):
    today = date.today()
    if start_date and end_date:
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            total_days = (end - start).days
            if total_days > 0:
                elapsed = max(0, (today - start).days)
                expected = min(100, round((elapsed / total_days) * 100))
                delta = progress - expected
                if delta >= -15:
                    return "green"
                elif delta >= -40:
                    return "amber"
                return "red"
        except ValueError:
            pass
    if progress >= 75:
        return "green"
    elif progress >= 40:
        return "amber"
    return "red"


def milestone_auto_progress(kpi):
    milestones = kpi.get("milestones", [])
    if not milestones:
        return kpi.get("progress_percent", 0)
    completed = sum(1 for m in milestones if m["status"] == "completed")
    return round((completed / len(milestones)) * 100)


def is_kpi_active(kpi):
    today = date.today()
    cutoff = today + timedelta(days=14)
    start_str = kpi.get("start_date", "")
    if start_str:
        try:
            start = date.fromisoformat(start_str)
            if start > cutoff:
                return False
        except ValueError:
            pass
    return kpi.get("progress_percent", 0) < 100


def member_summary(member):
    active = [k for k in member["kpis"] if is_kpi_active(k)]
    if not active:
        return {"progress": 0, "rag": "green", "next_deadline": None, "total": 0}
    avg = round(sum(k["progress_percent"] for k in active) / len(active))
    rag_order = {"red": 0, "amber": 1, "green": 2}
    worst_rag = min((k["rag_status"] for k in active), key=lambda r: rag_order[r])
    end_dates = [k["end_date"] for k in active if k.get("end_date")]
    next_deadline = min(end_dates) if end_dates else None
    return {"progress": avg, "rag": worst_rag, "next_deadline": next_deadline, "total": len(active)}


@app.route("/")
def team_overview():
    data = load_data()
    members_view = []
    for m in data["members"]:
        summary = member_summary(m)
        members_view.append({**m, **summary})
    return render_template("team_overview.html", members=members_view, data=data)


@app.route("/team-kpis")
def team_kpis():
    data = load_data()
    all_kpis = []
    for member in data["members"]:
        for kpi in member["kpis"]:
            active = is_kpi_active(kpi)
            all_kpis.append({**kpi, "member_name": member["name"], "member_id": member["id"], "is_active": active})
    rag_order = {"red": 0, "amber": 1, "green": 2}
    all_kpis.sort(key=lambda k: (0 if k["is_active"] else 1, rag_order.get(k["rag_status"], 1)))
    return render_template("team_kpis.html", all_kpis=all_kpis, data=data)


@app.route("/member/<member_id>")
def member_detail(member_id):
    data = load_data()
    member = next((m for m in data["members"] if m["id"] == member_id), None)
    if not member:
        return "Mitglied nicht gefunden", 404
    all_kpis = [{**k, "is_active": is_kpi_active(k)} for k in member["kpis"]]
    member_all = {**member, "kpis": all_kpis}
    summary = member_summary(member)
    return render_template("member_detail.html", member=member_all, summary=summary, data=data)


@app.route("/api/update_kpi", methods=["POST"])
def update_kpi():
    payload = request.get_json()
    member_id = payload.get("member_id")
    kpi_id = payload.get("kpi_id")
    progress = payload.get("progress_percent")
    notes = payload.get("notes")

    data = load_data()
    for member in data["members"]:
        if member["id"] == member_id:
            for kpi in member["kpis"]:
                if kpi["id"] == kpi_id:
                    if progress is not None:
                        kpi["progress_percent"] = int(progress)
                        kpi["rag_status"] = compute_rag(int(progress), kpi.get("start_date"), kpi.get("end_date"))
                    if notes is not None:
                        kpi["notes"] = notes
                    save_data(data)
                    return jsonify({"ok": True, "rag_status": kpi["rag_status"], "progress": kpi["progress_percent"]})
    return jsonify({"ok": False}), 404


@app.route("/api/update_milestone", methods=["POST"])
def update_milestone():
    payload = request.get_json()
    member_id = payload.get("member_id")
    kpi_id = payload.get("kpi_id")
    milestone_idx = payload.get("milestone_index")
    status = payload.get("status")

    data = load_data()
    for member in data["members"]:
        if member["id"] == member_id:
            for kpi in member["kpis"]:
                if kpi["id"] == kpi_id:
                    milestones = kpi.get("milestones", [])
                    if 0 <= milestone_idx < len(milestones):
                        milestones[milestone_idx]["status"] = status
                        new_progress = milestone_auto_progress(kpi)
                        new_rag = compute_rag(new_progress, kpi.get("start_date"), kpi.get("end_date"))
                        kpi["progress_percent"] = new_progress
                        kpi["rag_status"] = new_rag
                        save_data(data)
                        return jsonify({
                            "ok": True,
                            "progress": new_progress,
                            "rag_status": new_rag
                        })
    return jsonify({"ok": False}), 404


@app.route("/edit")
def edit():
    data = load_data()
    return render_template("edit.html", data=data)


@app.route("/api/save_all", methods=["POST"])
def save_all():
    payload = request.get_json()
    data = load_data()
    data["team_name"] = payload.get("team_name", data["team_name"])
    data["members"] = payload.get("members", data["members"])
    save_data(data)
    return jsonify({"ok": True})


@app.route("/upload", methods=["GET", "POST"])
def upload():
    data = load_data()
    if request.method == "POST":
        file = request.files.get("word_file")
        if not file or not file.filename.endswith(".docx"):
            return render_template("upload.html", error="Bitte eine .docx-Datei hochladen.", data=data)
        path = os.path.join(UPLOAD_FOLDER, "zielvereinbarungen.docx")
        file.save(path)
        try:
            import parse_goals
            parse_goals.parse(path)
            return redirect(url_for("team_overview"))
        except Exception as e:
            return render_template("upload.html", error=f"Fehler beim Einlesen: {e}", data=data)
    return render_template("upload.html", data=data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
