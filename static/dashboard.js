function saveProgress(memberId, kpiId) {
  var range = document.getElementById("range-" + kpiId);
  var progress = parseInt(range.value);
  fetch("/api/update_kpi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id: memberId, kpi_id: kpiId, progress_percent: progress })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.ok) {
      var bar = document.getElementById("bar-" + kpiId);
      bar.className = "progress-bar-inner " + data.rag_status;
      var card = document.getElementById("kpi-" + kpiId);
      card.className = card.className.replace(/rag-border-\w+/, "rag-border-" + data.rag_status);
      var badge = card.querySelector(".rag-badge:last-of-type");
      if (badge) { badge.className = "rag-badge " + data.rag_status; badge.textContent = data.rag_status.toUpperCase(); }
      flashBtn(card.querySelector(".btn-save"));
    }
  });
}

function saveNotes(memberId, kpiId) {
  var notes = document.getElementById("notes-" + kpiId).value;
  fetch("/api/update_kpi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id: memberId, kpi_id: kpiId, notes: notes })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.ok) {
      var btn = document.querySelector("#kpi-" + kpiId + " .notes-section .btn-save");
      flashBtn(btn);
    }
  });
}

function saveMilestone(select) {
  var memberId = select.dataset.member;
  var kpiId = select.dataset.kpi;
  var idx = parseInt(select.dataset.idx);
  var status = select.value;
  fetch("/api/update_milestone", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id: memberId, kpi_id: kpiId, milestone_index: idx, status: status })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.ok) {
      var li = document.getElementById("ms-" + kpiId + "-" + idx);
      li.className = li.className.replace(/status-\w+/, "status-" + status);
      var icon = li.querySelector(".ms-status-icon");
      if (status === "completed") icon.textContent = "✓";
      else if (status === "in_progress") icon.textContent = "◎";
      else icon.textContent = "○";
    }
  });
}

function flashBtn(btn) {
  if (!btn) return;
  btn.classList.add("success");
  btn.textContent = "Gespeichert ✓";
  setTimeout(function() {
    btn.classList.remove("success");
    btn.textContent = "Speichern";
  }, 1800);
}
