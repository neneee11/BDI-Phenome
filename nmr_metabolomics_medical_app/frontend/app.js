const appState = {
  summary: null,
  performance: null,
  features: null,
  trajectories: null,
  samples: [],
  selectedSample: null,
};

const $ = (selector) => document.querySelector(selector);
const TOP6 = ["Dimethyl sulfone", "L-valine", "isopropanol", "lipoproteins", "glycine", "L-leucine"];
const API_BASES = (() => {
  const params = new URLSearchParams(window.location.search);
  const explicitApi = params.get("api");
  if (explicitApi) return [explicitApi.replace(/\/$/, "")];

  const bases = [];
  const isBackendHost = ["8766", "8770"].includes(window.location.port);
  if (isBackendHost || window.location.protocol === "file:") bases.push("");
  if (!isBackendHost) {
    bases.push("http://127.0.0.1:8766");
    bases.push("http://127.0.0.1:8770");
  }
  return [...new Set(bases)];
})();

function apiUrl(base, path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${base}${path}`;
}

async function api(path, options = {}) {
  const bases = API_BASES.length ? API_BASES : [""];
  let lastError = null;

  for (const base of bases) {
    try {
      const response = await fetch(apiUrl(base, path), {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `API error ${response.status}`);
      return data;
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(
    `${lastError?.message || "cannot connect to backend"} | เปิด backend ก่อนด้วยคำสั่ง: python nmr_metabolomics_medical_app/backend/server.py --port 8766`,
  );
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function stateClass(value) {
  return String(value || "neutral").replace(/[^a-z0-9-]/gi, "-");
}

function setView(viewName) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active"));
  $(`#view-${viewName}`).classList.add("active");
  document.querySelector(`[data-view="${viewName}"]`).classList.add("active");
  const titles = {
    dashboard: "ภาพรวม",
    samples: "รายการตัวอย่าง",
    input: "นำเข้าข้อมูล",
    modeling: "ประสิทธิภาพโมเดล",
    rules: "คะแนนฟื้นตัว",
    assistant: "ผู้ช่วยถามตอบ",
    privacy: "ความปลอดภัย",
  };
  $("#pageTitle").textContent = titles[viewName] || viewName;
}

async function loadApp() {
  const [summary, performance, features, trajectories] = await Promise.all([
    api("/api/summary"),
    api("/api/performance"),
    api("/api/features"),
    api("/api/trajectories"),
  ]);
  appState.summary = summary;
  appState.performance = performance;
  appState.features = features;
  appState.trajectories = trajectories;

  renderSummary();
  renderPerformance();
  renderRules();
  renderManualInputs();
  renderTrajectory();
  await loadSamples();
  if (appState.samples.length) await selectSample(appState.samples[0].sample_name);
}

async function loadSamples() {
  const query = encodeURIComponent($("#sampleSearch")?.value?.trim() || "");
  const state = encodeURIComponent($("#stateFilter")?.value || "");
  const data = await api(`/api/samples?q=${query}&state=${state}&limit=160`);
  appState.samples = data.samples || [];
  renderSampleList();
}

function renderSummary() {
  const s = appState.summary;
  $("#heroAuc").textContent = s.metrics.roc_auc;
  $("#nSamples").textContent = s.n_samples;
  $("#nSubjects").textContent = s.n_subjects;
  $("#nMetabolites").textContent = s.n_metabolites;
  $("#nSelected").textContent = s.n_selected_features;

  const maxCount = Math.max(...s.timepoint_counts.map((item) => item.n), 1);
  $("#timepointBars").innerHTML = s.timepoint_counts
    .map(
      (item) => `
        <div class="bar-row">
          <strong>${escapeHtml(item.label)}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round((item.n / maxCount) * 100)}%"></div></div>
          <small>${item.n}</small>
        </div>
      `,
    )
    .join("");

  const featureDefs = Object.values(appState.features.feature_definitions || {});
  const maxImportance = Math.max(...featureDefs.map((f) => Number(f.importance || 0)), 0.001);
  $("#featureBars").innerHTML = featureDefs
    .sort((a, b) => Number(b.importance || 0) - Number(a.importance || 0))
    .map(
      (feature) => `
        <div class="bar-row">
          <strong>${escapeHtml(feature.metabolite)}</strong>
          <div class="bar-track">
            <div class="bar-fill" style="width:${Math.max(6, Math.round((feature.importance / maxImportance) * 100))}%"></div>
          </div>
          <small>${Number(feature.importance).toFixed(3)}</small>
        </div>
      `,
    )
    .join("");
}

function renderTrajectory() {
  const series = appState.trajectories.series || [];
  if (!series.length) return;

  const colors = ["#18a978", "#2b7fd7", "#6d5bd0", "#b77b16", "#2fb66d", "#d64b62"];
  const width = 920;
  const height = 300;
  const margin = { left: 64, top: 28, right: 32, bottom: 52 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const labels = series[0].points.map((point) => point.label);
  const x = (idx) => margin.left + (idx / Math.max(labels.length - 1, 1)) * plotW;
  const allValues = series.flatMap((item) => item.points.map((point) => Number(point.value)));
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const y = (value) => margin.top + (1 - (value - min) / Math.max(max - min, 0.001)) * plotH;

  const paths = series
    .map((item, idx) => {
      const color = colors[idx % colors.length];
      const d = item.points
        .map((point, pointIdx) => `${pointIdx === 0 ? "M" : "L"} ${x(pointIdx)} ${y(Number(point.value))}`)
        .join(" ");
      const circles = item.points
        .map((point, pointIdx) => `<circle cx="${x(pointIdx)}" cy="${y(Number(point.value))}" r="4" fill="${color}"></circle>`)
        .join("");
      return `<path d="${d}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"></path>${circles}`;
    })
    .join("");

  const axisLabels = labels
    .map((label, idx) => `<text x="${x(idx)}" y="${height - 18}" text-anchor="middle" fill="#648173" font-size="12">${label}</text>`)
    .join("");

  const legend = series
    .map(
      (item, idx) => `
        <span style="display:inline-flex;align-items:center;gap:6px;margin:6px 14px 0 0;color:#648173;font-size:12px">
          <i style="width:10px;height:10px;border-radius:999px;background:${colors[idx % colors.length]};display:inline-block"></i>
          ${escapeHtml(item.metabolite)}
        </span>
      `,
    )
    .join("");

  $("#trajectoryChart").innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Median metabolite trajectory">
      <rect x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}" rx="14" fill="#ffffff" stroke="#d8ebe1"></rect>
      ${[0, 0.25, 0.5, 0.75, 1]
        .map((tick) => `<line x1="${margin.left}" y1="${margin.top + tick * plotH}" x2="${width - margin.right}" y2="${margin.top + tick * plotH}" stroke="#e5f2eb"></line>`)
        .join("")}
      ${paths}
      ${axisLabels}
      <text x="18" y="150" transform="rotate(-90 18,150)" fill="#648173" font-size="12">median log1p abundance</text>
    </svg>
    <div>${legend}</div>
  `;
}

function renderSampleList() {
  const selectedName = appState.selectedSample?.sample_name;
  $("#sampleList").innerHTML =
    appState.samples
      .map(
        (sample) => `
          <div class="sample-item ${sample.sample_name === selectedName ? "active" : ""}" data-sample="${escapeHtml(sample.sample_name)}">
            <div class="row-between">
              <strong>${escapeHtml(sample.sample_name)}</strong>
              <span class="pill ${sample.recovery_state === "preop-like" ? "no" : ""}">${escapeHtml(sample.recovery_state)}</span>
            </div>
            <div class="row-between muted">
              <small>Subject ${escapeHtml(sample.subject_id)} | ${escapeHtml(sample.time_point)}</small>
              <small>${percent(sample.post_op_probability)}</small>
            </div>
          </div>
        `,
      )
      .join("") || `<p class="muted">No samples found.</p>`;

  document.querySelectorAll(".sample-item").forEach((item) => {
    item.addEventListener("click", () => selectSample(item.dataset.sample));
  });
}

async function selectSample(sampleName) {
  appState.selectedSample = await api(`/api/sample/${encodeURIComponent(sampleName)}`);
  renderSampleList();
  renderSelectedSample();
}

function renderSelectedSample() {
  const sample = appState.selectedSample;
  const pred = sample.prediction;
  $("#selectedSampleName").textContent = sample.sample_name;
  $("#selectedMeta").textContent = `Subject ${sample.subject_id} | ${sample.time_point} | label จริง: ${sample.label_name}`;
  $("#predictedLabel").textContent = pred.predicted_label_name;
  $("#postopProb").textContent = percent(pred.post_op_probability);
  $("#postopProbBar").style.width = percent(pred.post_op_probability);
  $("#recoveryScore").textContent = `${pred.rule_recovery_score} / 6`;
  $("#recoveryState").textContent = pred.rule_recovery_state;
  $("#followupFlag").textContent = thaiFollowupFlag(pred.nutrition_followup_flag);
  $("#ruleReasons").textContent = pred.rule_reasons;

  const badge = $("#stateBadge");
  badge.className = `badge ${stateClass(pred.rule_recovery_state)}`;
  badge.textContent = pred.rule_recovery_state;

  renderBiomarkerTable(pred.biomarkers || []);
  renderClinicalSummary();
  fillManualFromSelected();
  renderRules();
}

function thaiFollowupFlag(flag) {
  const map = {
    "closer dietitian follow-up": "ควรติดตามโภชนาการใกล้ชิด",
    "monitor next follow-up": "ติดตามซ้ำตามนัดถัดไป",
    "routine follow-up": "ติดตามตามแผนปกติ",
  };
  return map[flag] || flag || "--";
}

function makeClinicalSummary() {
  if (!appState.selectedSample) return "";
  const sample = appState.selectedSample;
  const pred = sample.prediction;
  const topReasons = (pred.matched_rules || []).map((rule) => rule.metabolite).slice(0, 3);
  const reasonText = topReasons.length ? topReasons.join(", ") : "ยังไม่มี rule ที่เข้า post-op-like direction";
  return [
    `Sample ${sample.sample_name} (Subject ${sample.subject_id}, ${sample.time_point})`,
    `ผลโมเดล: ${pred.predicted_label_name} | post-op probability ${percent(pred.post_op_probability)}.`,
    `Recovery score: ${pred.rule_recovery_score}/6 (${pred.rule_recovery_state}).`,
    `คำแนะนำระบบ: ${thaiFollowupFlag(pred.nutrition_followup_flag)}.`,
    `เหตุผลจาก biomarker: ${reasonText}.`,
    "หมายเหตุ: ใช้เป็น decision-support สำหรับทีมแพทย์/นักโภชนาการ ไม่ใช่คำวินิจฉัยโรค.",
  ].join(" ");
}

function renderClinicalSummary() {
  $("#clinicalSummaryText").textContent = makeClinicalSummary();
}

function renderBiomarkerTable(biomarkers) {
  $("#biomarkerTable").innerHTML = biomarkers
    .map(
      (item) => `
        <div class="bio-row">
          <strong>${escapeHtml(item.metabolite)}</strong>
          <span>z=${Number(item.scaled_value).toFixed(2)}</span>
          <span class="pill ${item.postop_like ? "" : "no"}">${item.postop_like ? "เข้าเกณฑ์" : "ไม่เข้าเกณฑ์"}</span>
          <small>${escapeHtml(item.metabolic_axis)}</small>
        </div>
      `,
    )
    .join("");
}

function renderManualInputs() {
  const features = appState.features?.selected_features || TOP6;
  $("#manualInputs").innerHTML = features
    .map(
      (feature) => `
        <div class="manual-row">
          <label>${escapeHtml(feature)}</label>
          <input class="input manual-metabolite" type="number" step="0.001" data-feature="${escapeHtml(feature)}" placeholder="log1p value" />
        </div>
      `,
    )
    .join("");
}

function fillManualFromSelected() {
  if (!appState.selectedSample) return;
  const values = appState.selectedSample.top6_metabolites || {};
  document.querySelectorAll(".manual-metabolite").forEach((input) => {
    input.value = values[input.dataset.feature] ?? "";
  });
}

function collectManualValues() {
  const metabolites = {};
  document.querySelectorAll(".manual-metabolite").forEach((input) => {
    metabolites[input.dataset.feature] = Number(input.value);
  });
  return metabolites;
}

async function predictManual() {
  try {
    const data = await api("/api/predict", {
      method: "POST",
      body: JSON.stringify({ value_type: "log1p", metabolites: collectManualValues() }),
    });
    $("#manualPrediction").innerHTML = predictionHtml(data.prediction);
  } catch (error) {
    $("#manualPrediction").innerHTML = `<strong style="color:var(--red)">Predict failed:</strong> ${escapeHtml(error.message)}`;
  }
}

function predictionHtml(prediction) {
  return `
    <div class="row-between">
      <strong>${escapeHtml(prediction.predicted_label_name)}</strong>
      <span class="pill ${prediction.rule_recovery_state === "preop-like" ? "no" : ""}">${escapeHtml(prediction.rule_recovery_state)}</span>
    </div>
    <p class="muted">
      post-op probability ${percent(prediction.post_op_probability)} |
      recovery score ${prediction.rule_recovery_score}/6 |
      ${escapeHtml(prediction.nutrition_followup_flag)}
    </p>
    <small>${escapeHtml(prediction.rule_reasons)}</small>
  `;
}

function parseDelimited(text) {
  const delimiter = text.split("\n")[0].includes("\t") ? "\t" : ",";
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  const headers = lines.shift().split(delimiter).map((header) => header.trim());
  return lines.map((line) => {
    const cells = line.split(delimiter);
    return Object.fromEntries(headers.map((header, idx) => [header, cells[idx]?.trim()]));
  });
}

function resolveFeature(row, feature) {
  if (feature in row) return Number(row[feature]);
  const match = Object.keys(row).find((key) => key.toLowerCase() === feature.toLowerCase());
  return match ? Number(row[match]) : NaN;
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const rows = parseDelimited(text).slice(0, 20);
  const features = appState.features?.selected_features || TOP6;
  const results = [];

  for (const [idx, row] of rows.entries()) {
    const metabolites = {};
    for (const feature of features) metabolites[feature] = resolveFeature(row, feature);
    if (Object.values(metabolites).some((value) => !Number.isFinite(value))) {
      results.push({ idx: idx + 1, error: "missing top-6 metabolite columns" });
      continue;
    }
    try {
      const data = await api("/api/predict", {
        method: "POST",
        body: JSON.stringify({
          sample_name: row["Sample Name"] || row.sample_name || `uploaded_row_${idx + 1}`,
          value_type: "log1p",
          metabolites,
        }),
      });
      results.push({ idx: idx + 1, prediction: data.prediction });
    } catch (error) {
      results.push({ idx: idx + 1, error: error.message });
    }
  }

  $("#uploadResult").innerHTML = results
    .map((item) => {
      if (item.error) return `<div class="bio-row"><strong>Row ${item.idx}</strong><span class="pill no">error</span><small>${escapeHtml(item.error)}</small></div>`;
      const pred = item.prediction;
      return `<div class="bio-row"><strong>Row ${item.idx}</strong><span>${escapeHtml(pred.predicted_label_name)}</span><span>${percent(pred.post_op_probability)}</span><small>${pred.rule_recovery_score}/6 ${escapeHtml(pred.rule_recovery_state)}</small></div>`;
    })
    .join("");
}

function renderPerformance() {
  const metrics = appState.performance.metrics;
  $("#mAuc").textContent = metrics.roc_auc;
  $("#mAcc").textContent = metrics.accuracy;
  $("#mF1").textContent = metrics.f1;
  $("#mGap").textContent = metrics.auc_gap;

  const cm = appState.performance.confusion_matrix.matrix;
  $("#confusionMatrix").innerHTML = `
    <table>
      <thead><tr><th>Actual / Pred</th><th>Preop</th><th>Post-op</th></tr></thead>
      <tbody>
        <tr><th>Preop</th><td class="good">${cm[0][0]}</td><td class="bad">${cm[0][1]}</td></tr>
        <tr><th>Post-op</th><td class="bad">${cm[1][0]}</td><td class="good">${cm[1][1]}</td></tr>
      </tbody>
    </table>
  `;

  const split = appState.performance.group_split.summary || [];
  $("#splitSummary").innerHTML = split
    .map(
      (item) => `
        <div class="split-item">
          <strong>${escapeHtml(item.split)}</strong>
          <p class="muted">${item.n_samples} samples | ${item.n_subjects} subjects | preop ${item.preop} | post-op ${item.postop}</p>
        </div>
      `,
    )
    .join("");
}

function renderRules() {
  const currentMatched = new Set((appState.selectedSample?.prediction?.matched_rules || []).map((rule) => rule.metabolite));
  const rules = [
    ["Dimethyl sulfone", "สูงขึ้น", "+1", "post-op metabolic change signal", "postop"],
    ["glycine", "สูงขึ้น", "+1", "metabolic health / insulin sensitivity", "postop"],
    ["L-valine", "ต่ำลง", "+1", "BCAA / insulin resistance / protein metabolism", "preop"],
    ["L-leucine", "ต่ำลง", "+1", "BCAA / amino acid metabolism", "preop"],
    ["lipoproteins", "ต่ำลง", "+1", "lipid metabolism / cardiometabolic risk", "preop"],
    ["isopropanol", "ต่ำลง", "+1", "ketone/alcohol metabolism", "preop"],
  ];
  $("#ruleCards").innerHTML = rules
    .map(
      ([metabolite, direction, score, axis, type]) => `
        <div class="rule-card ${type}">
          <div class="row-between">
            <strong>${escapeHtml(metabolite)}</strong>
            <span class="pill ${currentMatched.has(metabolite) ? "" : "no"}">${currentMatched.has(metabolite) ? "matched" : "rule"}</span>
          </div>
          <p>${escapeHtml(direction)} = ${score}</p>
          <small>${escapeHtml(axis)}</small>
        </div>
      `,
    )
    .join("");
}

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("#chatMessages").appendChild(div);
  $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
}

async function askAssistant(event) {
  event.preventDefault();
  const input = $("#assistantQuestion");
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  appendMessage("user", question);
  try {
    const data = await api("/api/assistant", {
      method: "POST",
      body: JSON.stringify({
        question,
        sample_name: appState.selectedSample?.sample_name,
      }),
    });
    appendMessage("ai", data.answer);
  } catch (error) {
    appendMessage("ai", `Error: ${error.message}`);
  }
}

function wireEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  let searchTimer = null;
  $("#sampleSearch").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadSamples, 180);
  });
  $("#stateFilter").addEventListener("change", loadSamples);
  $("#useSelectedBtn").addEventListener("click", fillManualFromSelected);
  $("#manualPredictBtn").addEventListener("click", predictManual);
  $("#fileInput").addEventListener("change", handleFileUpload);
  $("#assistantForm").addEventListener("submit", askAssistant);
  $("#copySummaryBtn").addEventListener("click", copyClinicalSummary);
  $("#printSummaryBtn").addEventListener("click", () => window.print());
}

wireEvents();
appendMessage("ai", "พร้อมช่วยอธิบาย sample ที่เลือก, ผลโมเดล, recovery score และเหตุผลจาก biomarker โดยเรียกผ่าน backend /api/assistant");
loadApp().catch((error) => {
  console.error(error);
  appendMessage("ai", `โหลดแอปไม่สำเร็จ: ${error.message}`);
});

async function copyClinicalSummary() {
  const text = makeClinicalSummary();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    $("#clinicalSummaryText").textContent = `${text}  (คัดลอกแล้ว)`;
  } catch {
    $("#clinicalSummaryText").textContent = text;
  }
}
