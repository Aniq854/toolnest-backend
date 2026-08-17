const $ = (id) => document.getElementById(id);

const inputEl = $("input");
const outputEl = $("output");
const statusEl = $("status");
const reportEl = $("report");

const wordCount = (t) => (t.trim() ? t.trim().split(/\s+/).length : 0);

function updateCounts() {
  $("inCount").textContent = `${wordCount(inputEl.value)} words`;
  $("outCount").textContent = `${wordCount(outputEl.value)} words`;
}
inputEl.addEventListener("input", updateCounts);
outputEl.addEventListener("input", updateCounts);

function setStatus(msg, isError = false) {
  if (!msg) {
    statusEl.hidden = true;
    return;
  }
  statusEl.hidden = false;
  statusEl.textContent = msg;
  statusEl.classList.toggle("error", isError);
}

async function api(method, url, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Error ${r.status}`);
  return data;
}

// ---------------- providers ----------------
(async () => {
  try {
    const { available } = await api("GET", "/api/providers");
    for (const p of available) {
      const o = document.createElement("option");
      o.value = p;
      o.textContent = p;
      $("provider").appendChild(o);
    }
  } catch {
    /* default kaafi hai */
  }
})();

// ---------------- quality report ----------------
const METRICS = [
  ["naturalness_score", "Naturalness", "up"],
  ["flesch_reading_ease", "Reading ease", "up"],
  ["sentence_len_stdev", "Sentence variety", "up"],
  ["avg_sentence_len", "Avg sentence", "flat"],
  ["cliche_hits", "Cliche phrases", "down"],
  ["bureaucracy_hits", "Bureaucratic", "down"],
  ["passive_hits", "Passive voice", "down"],
  ["long_word_pct", "Heavy words %", "down"],
  ["words", "Word count", "flat"],
];

function renderReport(before, after, tips) {
  const grid = $("metricGrid");
  grid.innerHTML = "";

  for (const [key, label, better] of METRICS) {
    const a = after[key];
    if (a === undefined) continue;
    const b = before ? before[key] : null;
    const tile = document.createElement("div");
    tile.className = "tile";

    let delta = "";
    if (b !== null && b !== undefined) {
      const diff = +(a - b).toFixed(2);
      if (diff !== 0 && better !== "flat") {
        const improved = better === "up" ? diff > 0 : diff < 0;
        delta = `<div class="d ${improved ? "up" : "down"}">${
          diff > 0 ? "+" : ""
        }${diff} vs before</div>`;
      } else if (diff !== 0) {
        delta = `<div class="d">${diff > 0 ? "+" : ""}${diff} vs before</div>`;
      }
    }

    tile.innerHTML = `<div class="k">${label}</div><div class="v">${a}</div>${delta}`;
    grid.appendChild(tile);
  }

  const ul = $("tips");
  ul.innerHTML = "";
  for (const t of tips || []) {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  }
  reportEl.hidden = false;
}

// ---------------- diff (sentence level) ----------------
const splitSentences = (t) =>
  t
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

$("diffBtn").addEventListener("click", () => {
  const box = $("diffBox");
  if (!outputEl.value.trim()) return;
  if (!box.hidden) {
    box.hidden = true;
    return;
  }

  const a = splitSentences(inputEl.value);
  const b = splitSentences(outputEl.value);
  const rows = Math.max(a.length, b.length);
  const wrap = $("diffContent");
  wrap.innerHTML = "";

  for (let i = 0; i < rows; i++) {
    const oldS = a[i] || "";
    const newS = b[i] || "";
    const same = oldS === newS;
    const row = document.createElement("div");
    row.className = "diff-row" + (same ? " same" : "");
    row.innerHTML = `
      <div class="diff-old">${escapeHtml(oldS) || "<em>&mdash;</em>"}</div>
      <div class="diff-new">${escapeHtml(newS) || "<em>&mdash;</em>"}</div>`;

    if (newS) {
      const btn = document.createElement("button");
      btn.className = "ghost tiny";
      btn.textContent = "Regenerate";
      btn.addEventListener("click", () => regenerate(btn, newS));
      row.querySelector(".diff-new").appendChild(btn);
    }
    wrap.appendChild(row);
  }
  box.hidden = false;
});

async function regenerate(btn, sentence) {
  btn.disabled = true;
  btn.textContent = "...";
  try {
    const { output } = await api("POST", "/api/rewrite-sentence", {
      sentence,
      tone: $("tone").value,
      provider: $("provider").value || null,
    });
    outputEl.value = outputEl.value.replace(sentence, output);
    updateCounts();
    btn.closest(".diff-row").querySelector(".diff-new").firstChild.textContent =
      output;
    setStatus("Jumla dobara likh diya gaya.");
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Regenerate";
  }
}

// ---------------- main actions ----------------
$("runBtn").addEventListener("click", async () => {
  const text = inputEl.value.trim();
  if (text.length < 20)
    return setStatus("Kam az kam 20 characters ka text daalein.", true);

  const btn = $("runBtn");
  btn.disabled = true;
  btn.textContent = "Working...";
  $("diffBox").hidden = true;
  setStatus("LLM rewrite kar raha hai... (lambe text mein 10-40 sec lag sakte hain)");

  try {
    const data = await api("POST", "/api/humanize", {
      text,
      tone: $("tone").value,
      reading_level: $("level").value,
      strength: Number($("strength").value),
      keep_length: $("keepLength").checked,
      provider: $("provider").value || null,
    });

    outputEl.value = data.output;
    updateCounts();
    renderReport(data.before, data.after, data.notes);
    setStatus(`Done — ${data.provider_used} / ${data.model_used}`);
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Humanize";
  }
});

$("analyzeBtn").addEventListener("click", async () => {
  const text = inputEl.value.trim();
  if (text.length < 20)
    return setStatus("Kam az kam 20 characters ka text daalein.", true);
  try {
    const data = await api("POST", "/api/analyze", { text });
    renderReport(null, data.metrics, data.suggestions);
    setStatus("Analysis mukammal (koi API call nahi hui — bilkul free).");
  } catch (e) {
    setStatus(e.message, true);
  }
});

$("copyBtn").addEventListener("click", async () => {
  if (!outputEl.value) return;
  await navigator.clipboard.writeText(outputEl.value);
  setStatus("Output copy ho gaya.");
});

$("downloadBtn").addEventListener("click", () => {
  if (!outputEl.value) return;
  const blob = new Blob([outputEl.value], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "humanized.txt";
  a.click();
  URL.revokeObjectURL(a.href);
});

updateCounts();
