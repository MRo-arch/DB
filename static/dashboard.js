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
      updateProgressUI(kpiId, data.progress, data.rag_status);
      var card = document.getElementById("kpi-" + kpiId);
      flashBtn(card.querySelector(".progress-controls .btn-save"));
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

      if (data.progress !== null && data.progress !== undefined) {
        updateProgressUI(kpiId, data.progress, data.rag_status);
        var rangeEl = document.getElementById("range-" + kpiId);
        if (rangeEl) rangeEl.value = data.progress;
        var rangeVal = document.getElementById("rangeval-" + kpiId);
        if (rangeVal) rangeVal.textContent = data.progress + "%";
      }
    }
  });
}

function updateProgressUI(kpiId, progress, ragStatus) {
  var bar = document.getElementById("bar-" + kpiId);
  if (bar) {
    bar.style.width = progress + "%";
    bar.className = "progress-bar-inner " + ragStatus;
  }
  var pct = document.getElementById("pct-" + kpiId);
  if (pct) pct.textContent = progress + "%";

  var card = document.getElementById("kpi-" + kpiId);
  if (card) {
    card.className = card.className.replace(/rag-border-\w+/, "rag-border-" + ragStatus);
    var badge = card.querySelector(".kpi-card-header .rag-badge");
    if (badge) { badge.className = "rag-badge " + ragStatus; badge.textContent = ragStatus.toUpperCase(); }
  }
}

function flashBtn(btn) {
  if (!btn) return;
  var orig = btn.textContent;
  btn.classList.add("success");
  btn.textContent = "Gespeichert ✓";
  setTimeout(function() {
    btn.classList.remove("success");
    btn.textContent = orig;
  }, 1800);
}

document.querySelectorAll(".progress-range").forEach(function(range) {
  range.addEventListener("input", function() {
    var kpiId = this.dataset.kpi;
    document.getElementById("rangeval-" + kpiId).textContent = this.value + "%";
    document.getElementById("pct-" + kpiId).textContent = this.value + "%";
    document.getElementById("bar-" + kpiId).style.width = this.value + "%";
  });
});
