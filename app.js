"use strict";

// Independent-binomial Newcombe (1998) method 10; outcome is an adverse event.
(function () {
  const Z = { "0.9": 1.6448536269514722, "0.95": 1.959963984540054, "0.99": 2.5758293035489004 };
  const INPUTS = ["control_events", "control_total", "treatment_events", "treatment_total"];
  const OUTPUTS = ["control_risk", "treatment_risk", "absolute_risk_reduction", "arr_ci_lower", "arr_ci_upper", "relative_risk", "relative_risk_reduction", "measure", "number_needed", "number_needed_rounded_up", "number_needed_ci_lower", "number_needed_ci_upper", "ci_crosses_zero"];

  function wilson(x, n, z) {
    const p = x / n, zz = z * z, den = 1 + zz / n;
    const mid = (p + zz / (2 * n)) / den;
    const half = z * Math.sqrt(p * (1 - p) / n + zz / (4 * n * n)) / den;
    return [Math.max(0, mid - half), Math.min(1, mid + half)];
  }

  function calculate(input, confidence) {
    const key = String(confidence === undefined ? 0.95 : confidence);
    if (!Object.prototype.hasOwnProperty.call(Z, key)) {
      throw new Error("Choose a supported confidence level (90%, 95%, 99%).");
    }
    for (const name of INPUTS) {
      if (!Number.isSafeInteger(input[name]) || input[name] < 0) {
        throw new Error(name + " must be a non-negative whole number.");
      }
    }
    if (!input.control_total || !input.treatment_total ||
        input.control_events > input.control_total ||
        input.treatment_events > input.treatment_total) {
      throw new Error("Participants must be greater than zero; events cannot exceed participants.");
    }
    const pc = input.control_events / input.control_total;
    const pt = input.treatment_events / input.treatment_total;
    const arr = pc - pt;
    const c = wilson(input.control_events, input.control_total, Z[key]);
    const t = wilson(input.treatment_events, input.treatment_total, Z[key]);
    const low = Math.max(-1, arr - Math.hypot(pc - c[0], t[1] - pt));
    const high = Math.min(1, arr + Math.hypot(c[1] - pc, pt - t[0]));
    const crosses = low <= 0 && high >= 0;
    const number = arr ? 1 / Math.abs(arr) : null;
    const ci = crosses ? null : [Math.min(1 / Math.abs(low), 1 / Math.abs(high)), Math.max(1 / Math.abs(low), 1 / Math.abs(high))];
    return {
      control_risk: pc, treatment_risk: pt, absolute_risk_reduction: arr,
      risk_difference_ci: [low, high],
      relative_risk: pc ? pt / pc : null,
      relative_risk_reduction: pc ? arr / pc : null,
      measure: arr > 0 ? "NNT" : arr < 0 ? "NNH" : "no_difference",
      number_needed: number,
      number_needed_rounded_up: number === null ? null : Math.ceil(number - 1e-12),
      number_needed_ci: ci, ci_crosses_zero: crosses,
      confidence_level: Number(key), method: "Newcombe-Wilson score, no continuity correction"
    };
  }

  function count(raw, label) {
    if (!/^\d+$/.test(String(raw).trim())) {
      throw new Error(label + " must be a non-negative integer.");
    }
    const n = Number(raw);
    if (!Number.isSafeInteger(n)) throw new Error(label + " exceeds the supported integer range.");
    return n;
  }

  function parseCSV(text) {
    const rows = [], row = [];
    let value = "", quoted = false, afterQuote = false;
    text = text.replace(/^\uFEFF/, "");
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"') {
          if (text[i + 1] === '"') { value += '"'; i++; } else { quoted = false; afterQuote = true; }
        } else { value += ch; }
      } else if (ch === ",") {
        row.push(value); value = ""; afterQuote = false;
      } else if (ch === "\r" || ch === "\n") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(value);
        if (!(row.length === 1 && row[0] === "")) rows.push(row.slice());
        row.length = 0; value = ""; afterQuote = false;
      } else if (ch === '"' && value === "" && !afterQuote) {
        quoted = true;
      } else if (ch === '"' || afterQuote) {
        throw new Error("Malformed CSV quoting.");
      } else {
        value += ch;
      }
    }
    if (quoted) throw new Error("Unclosed quoted CSV field.");
    if (value !== "" || row.length) { row.push(value); rows.push(row); }
    return rows;
  }

  function escapeCell(value, untrusted) {
    let str = value === null || value === undefined ? "" : String(value);
    if (untrusted && /^[\s]*[=+\-@]/.test(str)) str = "'" + str;
    return '"' + str.replace(/"/g, '""') + '"';
  }

  function makeCSV(rows, headers, originalHeaders) {
    return [headers.map(h => escapeCell(h, false)).join(",")].concat(
      rows.map(row => headers.map(h => escapeCell(row[h], originalHeaders.indexOf(h) !== -1 && OUTPUTS.indexOf(h) === -1)).join(","))
    ).join("\r\n") + "\r\n";
  }

  function batchFromCSV(csv, confidence) {
    const records = parseCSV(csv);
    if (!records.length) throw new Error("CSV is empty.");
    const headers = records[0].map(x => x.trim());
    if (new Set(headers).size !== headers.length || INPUTS.some(h => headers.indexOf(h) < 0)) {
      throw new Error("CSV must have unique headers including: " + INPUTS.join(", "));
    }
    if (records.length - 1 > 4000) throw new Error("Limit: 4,000 data rows.");
    const output = [];
    records.slice(1).forEach((values, i) => {
      if (values.length !== headers.length) throw new Error("Row " + (i + 2) + ": wrong number of CSV fields.");
      const row = {};
      headers.forEach((h, index) => { row[h] = values[index]; });
      try {
        const input = {};
        INPUTS.forEach(h => { input[h] = count(row[h], h); });
        const r = calculate(input, confidence);
        row.control_risk = r.control_risk;
        row.treatment_risk = r.treatment_risk;
        row.absolute_risk_reduction = r.absolute_risk_reduction;
        row.arr_ci_lower = r.risk_difference_ci[0];
        row.arr_ci_upper = r.risk_difference_ci[1];
        row.relative_risk = r.relative_risk;
        row.relative_risk_reduction = r.relative_risk_reduction;
        row.measure = r.measure;
        row.number_needed = r.number_needed;
        row.number_needed_rounded_up = r.number_needed_rounded_up;
        row.number_needed_ci_lower = r.number_needed_ci && r.number_needed_ci[0];
        row.number_needed_ci_upper = r.number_needed_ci && r.number_needed_ci[1];
        row.ci_crosses_zero = r.ci_crosses_zero;
        output.push(row);
      } catch (err) { throw new Error("Row " + (i + 2) + ": " + err.message); }
    });
    return makeCSV(output, [...new Set([...headers, ...OUTPUTS])], headers);
  }

  // CommonJS export allows dependency-free mathematical and parser regression tests in Node.
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { calculate, count, parseCSV, batchFromCSV, wilson };
  }
  if (typeof document === "undefined") return;

  const byId = id => document.getElementById(id);
  const pct = n => (n * 100).toFixed(2) + "%";
  let lastResult = null;
  function saveFile(name, csv) {
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function render(r) {
    byId("measure").textContent = r.measure === "no_difference" ? "No observed difference" : r.measure;
    byId("number-needed").textContent = r.number_needed_rounded_up === null ? "Not finite" : r.number_needed_rounded_up.toLocaleString();
    byId("number-description").textContent = r.measure === "NNT" ? "People treated per one fewer adverse event (whole-person rounding up)" :
      r.measure === "NNH" ? "People treated per one additional adverse event (whole-person rounding up)" : "Equal observed event risks";
    byId("control-risk").textContent = pct(r.control_risk);
    byId("treatment-risk").textContent = pct(r.treatment_risk);
    byId("arr").textContent = pct(r.absolute_risk_reduction);
    byId("rr").textContent = r.relative_risk === null ? "Undefined" : r.relative_risk.toFixed(3);
    byId("ci-title").textContent = (r.confidence_level * 100).toFixed(0) + "% confidence interval";
    byId("ci-description").textContent = "ARR: " + pct(r.risk_difference_ci[0]) + " to " + pct(r.risk_difference_ci[1]) +
      (r.number_needed_ci ? "; " + r.measure + ": " + r.number_needed_ci[0].toFixed(2) + " to " + r.number_needed_ci[1].toFixed(2) : "");
    const info = byId("interpretation");
    info.classList.toggle("bad", r.ci_crosses_zero);
    info.textContent = r.ci_crosses_zero
      ? "The risk-difference interval includes zero. A finite NNT/NNH confidence interval is not defined; the compatible effects span benefit and harm."
      : (r.measure === "NNT" ? "The observed treatment group has fewer adverse events. " : "The observed treatment group has more adverse events. ") +
        "The entire score confidence interval is on the same side of the null.";
    byId("download-one").disabled = false;
  }
  function formInput() {
    const obj = {};
    INPUTS.forEach(name => { obj[name] = count(byId(name).value, name); });
    return obj;
  }
  function run(event) {
    if (event) event.preventDefault();
    byId("error").textContent = "";
    try {
      const inputs = formInput(), r = calculate(inputs, byId("confidence").value);
      lastResult = { inputs, result: r };
      render(r);
    } catch (err) { byId("error").textContent = err.message; }
  }
  byId("calculator").addEventListener("submit", run);
  byId("sample").addEventListener("click", () => {
    [120, 1000, 80, 1000].forEach((n, i) => { byId(INPUTS[i]).value = n; });
    byId("confidence").value = "0.95"; run();
  });
  byId("download-one").addEventListener("click", () => {
    if (!lastResult) return;
    const r = lastResult.result, row = { ...lastResult.inputs,
      ...r, arr_ci_lower: r.risk_difference_ci[0], arr_ci_upper: r.risk_difference_ci[1],
      number_needed_ci_lower: r.number_needed_ci && r.number_needed_ci[0],
      number_needed_ci_upper: r.number_needed_ci && r.number_needed_ci[1] };
    saveFile("nnt-result.csv", makeCSV([row], [...INPUTS, ...OUTPUTS], []));
  });
  byId("batch-button").addEventListener("click", async () => {
    const status = byId("batch-status"), file = byId("batch-file").files[0];
    status.textContent = "";
    if (!file) { status.textContent = "Select a CSV file."; return; }
    if (file.size > 1024 * 1024) { status.textContent = "File exceeds 1 MB."; return; }
    try {
      const csv = batchFromCSV(await file.text(), byId("confidence").value);
      saveFile("nnt-batch-results.csv", csv);
      status.textContent = "Results exported locally.";
    } catch (err) { status.textContent = "Error: " + err.message; }
  });
  run();
}());
