from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "kpis.json")


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_rag(progress):
    if progress >= 75:
        return "green"
    elif progress >= 40:
        return "amber"
    return "red"


def member_summary(member):
    kpis = member["kpis"]
    if not kpis:
        return {"progress": 0, "rag": "red", "next_deadline": None, "total": 0}
    avg = round(sum(k["progress_percent"] for k in kpis) / len(kpis))
    rag_order = {"red": 0, "amber": 1, "green": 2}
    worst_rag = min((k["rag_status"] for k in kpis), key=lambda r: rag_order[r])
    all_deadlines = [
        m["deadline"]
        for k in kpis
        for m in k.get("milestones", [])
        if m["status"] != "completed"
    ]
    next_deadline = min(all_deadlines) if all_deadlines else None
    return {"progress": avg, "rag": worst_rag, "next_deadline": next_deadline, "total": len(kpis)}


@app.route("/")
def team_overview():
    data = load_data()
    members_view = []
    for m in data["members"]:
        summary = member_summary(m)
        members_view.append({**m, **summary})
    return render_template("team_overview.html", members=members_view, data=data)


@app.route("/member/<member_id>")
def member_detail(member_id):
    data = load_data()
    member = next((m for m in data["members"] if m["id"] == member_id), None)
    if not member:
        return "Mitglied nicht gefunden", 404
    summary = member_summary(member)
    return render_template("member_detail.html", member=member, summary=summary, data=data)


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
                        kpi["rag_status"] = compute_rag(int(progress))
                    if notes is not None:
                        kpi["notes"] = notes
                    save_data(data)
                    return jsonify({"ok": True, "rag_status": kpi["rag_status"]})
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
                        save_data(data)
                        return jsonify({"ok": True})
    return jsonify({"ok": False}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
