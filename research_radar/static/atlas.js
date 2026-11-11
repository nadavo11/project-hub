/* Only persisted observations. Filtering never changes the reported experiment. */
(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (value, digits = 2) => typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "Not measured";
  const percent = value => typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Not measured";
  const methods = { roma: "RoMa · gate 0.20", "roma-005": "RoMa · gate 0.05", "roma-official": "RoMa · upstream sample", sift: "SIFT + mutual ratio", orb: "ORB + mutual ratio" };
  const url = new URL(location.href);
  let cohort, current, measured, requestId = 0;
  let method = Object.hasOwn(methods, url.searchParams.get("method")) ? url.searchParams.get("method") : "roma";
  let caseId = url.searchParams.get("case") || "";
  let minimum = 0, inliers = false, lines = true, heatmap = false, color = "confidence", selected = -1;

  async function get(path) {
    const response = await fetch(path, { cache: "no-store", credentials: "same-origin" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  }
  function error(message) {
    $("#atlas-error").textContent = message;
    $("#atlas-error").hidden = !message;
  }
  function stat(value, label, detail) {
    return `<article class="atlas-stat"><strong>${esc(value)}</strong><span>${esc(label)}</span><small>${esc(detail)}</small></article>`;
  }
  function metric(label, value) { return `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`; }
  function stage(number, label, value, good) {
    return `<div class="atlas-stage ${good ? "good" : "warn"}"><span>${number} / ${esc(label)}</span><strong>${esc(value)}</strong></div>`;
  }
  function outcome(row) { return row.methods[method]?.stage || "Not run"; }

  function summary() {
    const completed = cohort.cases.reduce((count, row) => count + Object.keys(row.methods).length, 0);
    const verified = cohort.cases.filter(row => row.geography.status === "identity verified").length;
    const metricCases = cohort.cases.filter(row => row.camera.metric_pose_supported).length;
    $("#run-state").textContent = cohort.complete ? "Measured cohort complete" : `${completed} / ${cohort.cases.length * (cohort.method_count || 3)} measured analyses`;
    $("#atlas-summary").innerHTML =
      stat(cohort.cases.length, "Real cross-domain pairs", "24 DenseUAV identities · 3 AnyVisLoc scenes") +
      stat(`${verified} / ${cohort.cases.length}`, "Identity-verified retrieved regions", "Other crops: scene known, overlap unresolved") +
      stat(`${metricCases} / ${cohort.cases.length}`, "Pairs with metric pose prerequisites", "Calibration + map frame + DSM required") +
      stat("0", "Pairs with verified point ground truth", "No precision or PCK invented");
    $("#frequency").innerHTML = `<table><thead><tr><th>Dataset / baseline</th><th>Observed stopping point</th><th>Count / measured</th></tr></thead><tbody>${Object.entries(cohort.counts).flatMap(([group, counts]) => {
      const total = Object.values(counts).reduce((a, b) => a + b, 0);
      return Object.entries(counts).map(([name, count]) => `<tr><td>${esc(group)}</td><td>${esc(name)}</td><td>${count} / ${total} · ${percent(count / total)}</td></tr>`);
    }).join("")}</tbody></table><p class="hint">Per-dataset denominators; frames within a scene are correlated. Stopping points are observations, not uniquely identified causes.</p>`;
    const previous = $("#stage-filter").value;
    $("#stage-filter").innerHTML = '<option value="">All outcomes</option>' +
      [...new Set(cohort.cases.map(outcome))].sort().map(value => `<option>${esc(value)}</option>`).join("");
    if ([...$("#stage-filter").options].some(o => o.value === previous)) $("#stage-filter").value = previous;
    $("#atlas-findings").innerHTML = (cohort.findings || []).map(finding => `<article><h3>${esc(finding.title)}</h3><p>${esc(finding.observation)}</p><a href="/atlas.html?case=${encodeURIComponent(finding.case_id)}&method=${encodeURIComponent(finding.method)}">Inspect measured case ↗</a></article>`).join("");
  }

  function caseList() {
    const search = $("#case-search").value.toLowerCase(), dataset = $("#dataset-filter").value, filter = $("#stage-filter").value;
    const rows = cohort.cases.filter(row => (!dataset || row.dataset === dataset) && (!filter || outcome(row) === filter) &&
      `${row.id} ${row.query_id} ${row.scene}`.toLowerCase().includes(search));
    $("#case-count").textContent = `${rows.length} of ${cohort.cases.length} cases · ${methods[method]}`;
    $("#case-list").innerHTML = rows.length ? rows.map(row =>
      `<button class="atlas-case" data-case="${esc(row.id)}" aria-pressed="${row.id === caseId}"><small>${esc(row.dataset)} / ${esc(row.scene)}</small><strong>${esc(row.query_id)}</strong><small class="case-outcome">${esc(outcome(row))}</small></button>`).join("") :
      '<div class="empty"><p>No cases match these filters. Clear the search or choose another outcome.</p></div>';
  }

  async function choose(identifier) {
    caseId = identifier;
    const token = ++requestId;
    current = cohort.cases.find(row => row.id === caseId);
    if (!current) return;
    caseList();
    selected = -1;
    const next = new URL(location.href);
    next.searchParams.set("case", caseId); next.searchParams.set("method", method);
    history.replaceState(null, "", next);
    $("#atlas-detail").setAttribute("aria-busy", "true");
    $("#atlas-detail").innerHTML = `<div class="empty"><h2>Reading ${esc(current.query_id)}</h2><p>Loading saved ${esc(methods[method])} measurements.</p></div>`;
    try {
      const result = current.methods[method] ? await get(`/api/atlas/cases/${encodeURIComponent(caseId)}/${method}`) : null;
      if (token !== requestId) return;
      measured = result;
      error("");
      detail();
    } catch (e) {
      if (token !== requestId) return;
      error(e.message);
      $("#atlas-detail").innerHTML = '<div class="empty"><h2>Measurement could not load</h2><p>Use Refresh measurements to retry. No previous case is presented as this one.</p></div>';
    } finally { if (token === requestId) $("#atlas-detail").setAttribute("aria-busy", "false"); }
  }

  function detail() {
    const head = `<div class="atlas-detail-head"><div><span class="eyebrow">${esc(current.dataset)} / ${esc(current.scene)}</span><h2>${esc(current.query_id)}</h2><p>${esc(current.target_id)}</p></div><div class="atlas-methods" role="group" aria-label="Matching baseline">${Object.entries(methods).map(([key, title]) => `<button data-method="${key}" aria-pressed="${method === key}">${title}</button>`).join("")}</div></div>`;
    if (!measured) {
      $("#atlas-detail").innerHTML = head + '<div class="empty"><h3>This baseline has not completed</h3><p>Choose an available baseline or refresh after inference. Missing results are not failures or successes.</p></div>';
      return;
    }
    const m = measured, p = m.pose, h = m.homography;
    const depth = cohort.depth_controls?.find(row => row.case_id === caseId && row.method === method);
    const poseText = p.status === "unsupported" ? "Metric pose unsupported" : p.status === "estimated" ? `${num(p.horizontal_error_m)} m horizontal error` : "No accepted pose";
    $("#atlas-detail").innerHTML = head +
      `<div class="atlas-stages">${stage("01", "Geography", current.geography.status, current.geography.status === "identity verified")}${stage("02", "Matching", `${m.count} retained · accuracy unknown`, false)}${stage("03", "Geometry", current.camera.metric_pose_supported ? "K + distortion + DSM available" : "Metric constraints missing", current.camera.metric_pose_supported)}${stage("04", "Pose", poseText, p.status === "estimated" && p.horizontal_error_m !== null && p.horizontal_error_m <= 10)}</div>
      <div class="atlas-viewer"><div class="atlas-viewer-head"><span>DRONE · ${current.query_size.join(" × ")} px</span><span>SATELLITE · ${current.target_size.join(" × ")} px</span></div>
      <svg id="match-view" viewBox="0 0 1344 500" role="img" aria-label="Original image pair with measured correspondence overlays"></svg>
      <div class="atlas-view-controls">
        <label>Minimum score <input id="match-confidence" aria-label="Minimum match confidence" type="range" min="0" max="1" step="0.01" value="${minimum}"><output id="confidence-value">${minimum.toFixed(2)}</output></label>
        <label><input id="inliers-only" type="checkbox" ${inliers ? "checked" : ""}> Homography inliers only</label>
        <label><input id="show-lines" type="checkbox" ${lines ? "checked" : ""}> Show links</label>
        ${method.startsWith("roma") ? `<label><input id="show-confidence" type="checkbox" ${heatmap ? "checked" : ""}> Raw confidence map</label>` : ""}
        <label>Color<select id="match-color"><option value="confidence">Native score</option><option value="homography">Homography residual</option><option value="pose">PnP residual</option></select></label>
        <label>Inspect match<input id="match-index" type="number" min="0" max="${Math.max(0, m.count - 1)}" aria-label="Inspect match index" placeholder="Index"></label>
      </div><div class="atlas-legend" id="match-legend"></div><div class="atlas-match-inspector" id="match-inspector">Select a correspondence or enter its index to inspect exact measurements.</div></div>
      <div class="atlas-note"><strong>Observed stopping point: ${esc(m.stage)}.</strong> ${esc(m.causal_status)}</div>
      <div class="atlas-evidence-grid">
        <section class="atlas-evidence"><h3>Matching & spatial support</h3><dl class="atlas-metrics">
          ${metric("Detected query / target features", `${m.counts.detected_query ?? "Dense lattice"} / ${m.counts.detected_target ?? "Dense prediction"}`)}
          ${metric("Retained correspondences", m.count)}${metric("Query convex-hull coverage", percent(m.query_coverage.hull_fraction))}
          ${m.counts.dense_lattice != null ? metric("Native prediction lattice", m.counts.dense_lattice) : ""}
          ${m.counts.certainty_eligible != null ? metric("Native cells passing confidence gate", m.counts.certainty_eligible) : ""}
          ${metric("Target convex-hull coverage", percent(m.target_coverage.hull_fraction))}${metric("Query occupied 8×8 cells", percent(m.query_coverage.occupied_grid_fraction))}
          ${metric("Homography inliers (not GT)", h.inliers)}${metric("Homography residual / target pixels", num(h.median_inlier_residual_px))}
          ${metric("Ground-truth point accuracy", "Unavailable")}</dl><p class="space-top">${esc(m.confidence_semantics)}</p></section>
        <section class="atlas-evidence"><h3>Metric geometry & pose</h3><dl class="atlas-metrics">
          ${metric("Pose status", p.status)}${metric("Valid DSM lifts", m.depth?.valid ?? "No DSM")}
          ${metric("DSM spacing / metres", m.depth?.dsm_resolution_m?.map(v => num(v)).join(" × ") || "Unavailable")}
          ${metric("3D second/first singular value", num(m.geometry?.axis_ratio, 4))}
          ${metric("3D third/first singular value", num(m.geometry?.planarity_ratio, 4))}
          ${metric("Positive-depth pose inliers", p.inliers ?? "Not run")}${metric("Pose inlier residual / query pixels", num(p.residual_median_px))}
          ${metric("Horizontal camera error / metres", num(p.horizontal_error_m))}</dl>
          <p class="space-top">${esc(p.reason || "Error uses released SfM-refined horizontal camera position, not independently surveyed 6-DoF truth. Planarity alone is not proof of degeneracy.")}</p></section>
        <section class="atlas-evidence"><h3>Controlled alternatives · same matches</h3>${Object.keys(m.controls).length ?
          `<table class="atlas-controls-table"><thead><tr><th>Intervention</th><th>Inliers</th><th>XY error / m</th></tr></thead><tbody>${Object.entries(m.controls).map(([key, value]) => `<tr><td>${esc(key.replaceAll("_", " "))}</td><td>${value.inliers}</td><td>${num(value.horizontal_error_m)}</td></tr>`).join("")}</tbody></table><p class="space-top">Deliberate camera/depth perturbations and an EPNP solver control. A lower error does not establish that the perturbed assumption is correct.</p>` :
          `<p>Not run: verified metric geometry is unavailable. Neither a homography nor altitude labels supply calibrated 6-DoF pose.</p>`}</section>
        <section class="atlas-evidence"><h3>Evidence boundary</h3><p>${esc(current.geography.evidence)}</p><p class="space-top">${esc(m.point_accuracy_reason)}</p>
          <dl class="atlas-metrics space-top">${metric("New execution device", m.device)}${metric("Measured CPU seconds", num(m.cpu_seconds))}${metric("Wall seconds", num(m.wall_seconds))}</dl>
          <div class="actions space-top"><a class="button small" href="/api/atlas/cases/${encodeURIComponent(caseId)}" target="_blank" rel="noopener">Source & camera record ↗</a><a class="button small" href="/api/atlas/cases/${encodeURIComponent(caseId)}/${method}" download="${esc(caseId)}-${method}.json">Export measurements</a></div>
        </section>${depth ? `<section class="atlas-evidence"><h3>Depth-provider intervention · common support</h3><p>${depth.common_valid_matches} / ${depth.original_matches} matches valid in both DSMs. Satellite images, match XY, calibration and solver settings are unchanged.</p>
        <table class="atlas-controls-table"><thead><tr><th>Height source / solver</th><th>Inliers</th><th>XY error / m</th></tr></thead><tbody>${Object.entries(depth.results).map(([key, value]) => `<tr><td>${esc(key.replaceAll("_", " "))}</td><td>${value.inliers}</td><td>${num(value.horizontal_error_m)}</td></tr>`).join("")}</tbody></table>
        <p class="space-top">Satellite DSM spacing 30 m; aerial DSM 0.25–0.65 m. This changes provider, resolution and possibly acquisition epoch—not resolution alone. No better setting is selected using ground truth.</p></section>` : ""}</div>`;
    $("#match-color").value = color;
    draw();
  }

  function fit(size, left) {
    const scale = Math.min(640 / size[0], 480 / size[1]);
    return { x: left + (640 - scale * size[0]) / 2, y: 10 + (480 - scale * size[1]) / 2, w: size[0] * scale, h: size[1] * scale, scale };
  }
  function draw() {
    if (!measured || !$("#match-view")) return;
    const a = fit(current.query_size, 0), b = fit(current.target_size, 704);
    const candidates = measured.matches.map((m, i) => ({ m, i })).filter(({ m }) => m.confidence >= minimum && (!inliers || m.h_inlier));
    const shown = candidates.length > 160 ? Array.from({ length: 160 }, (_, i) => candidates[Math.floor(i * candidates.length / 160)]) : [...candidates];
    if (selected >= 0 && measured.matches[selected] && !shown.some(row => row.i === selected)) shown.push({ m: measured.matches[selected], i: selected });
    const segment = ({ m, i }) => {
      const value = color === "confidence" ? m.confidence : color === "homography" ? m.h_residual : m.p_residual;
      const hue = value == null ? "#8290aa" : color === "confidence" ? (value >= .5 ? "#83d9e0" : "#e8c38b") : (value <= (color === "pose" ? 8 : 4) ? "#83d9e0" : "#f3a5af");
      const x1 = a.x + (m.q[0] + .5) * a.scale, y1 = a.y + (m.q[1] + .5) * a.scale;
      const x2 = b.x + (m.t[0] + .5) * b.scale, y2 = b.y + (m.t[1] + .5) * b.scale;
      return `${lines || i === selected ? `<line class="match-line ${i === selected ? "selected" : ""}" data-match="${i}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${hue}"><title>Match ${i} · score ${num(m.confidence)}</title></line>` : ""}<circle class="match-dot" data-match="${i}" cx="${x1}" cy="${y1}" r="${i === selected ? 5 : 2}" fill="${hue}"/><circle class="match-dot" data-match="${i}" cx="${x2}" cy="${y2}" r="${i === selected ? 5 : 2}" fill="${hue}"/>`;
    };
    $("#match-view").innerHTML = `<title>${esc(current.query_id)} matched with ${esc(current.target_id)}</title><image href="/atlas-assets/${encodeURIComponent(caseId)}/query.png" x="${a.x}" y="${a.y}" width="${a.w}" height="${a.h}"/><image href="/atlas-assets/${encodeURIComponent(caseId)}/target.png" x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}"/>${heatmap && method.startsWith("roma") ? `<image href="/atlas-assets/${encodeURIComponent(caseId)}/confidence.png" x="${a.x}" y="${a.y}" width="${a.w}" height="${a.h}" preserveAspectRatio="none"/>` : ""}${shown.filter(r => r.i !== selected).map(segment).join("")}${shown.filter(r => r.i === selected).map(segment).join("")}`;
    $("#match-legend").textContent = `${candidates.length} / ${measured.count} matches meet display filters; drawing ${shown.length} systematic samples${selected >= 0 ? " (including inspected match)" : ""}. ${color === "confidence" ? "Cyan ≥0.50; amber <0.50 native score (not accuracy)." : `Cyan within ${color === "pose" ? 8 : 4}px; pink above threshold; gray unavailable. Residual is self-fit, not GT.`}`;
    if (heatmap && method.startsWith("roma")) $("#match-legend").textContent += " Raw query heatmap: pink <0.05, amber 0.05–0.20, cyan ≥0.20. No per-image renormalization.";
    const m = measured.matches[selected];
    if (m) {
      $("#match-index").value = selected;
      $("#match-inspector").innerHTML = `<strong>Match ${selected}</strong> · query (${m.q.map(v => num(v, 1)).join(", ")}) → target (${m.t.map(v => num(v, 1)).join(", ")}) · score ${num(m.confidence, 3)} · H residual ${num(m.h_residual)} target px · PnP residual ${num(m.p_residual)} query px · correctness unknown`;
    }
  }

  async function refresh() {
    $("#atlas-refresh").disabled = true;
    try {
      cohort = await get("/api/atlas");
      error(""); summary(); caseList();
      await choose(cohort.cases.some(row => row.id === caseId) ? caseId : cohort.cases[0]?.id);
    } catch (e) { error(`${e.message}. Existing records have not been replaced. Refresh to retry.`); }
    finally { $("#atlas-refresh").disabled = false; }
  }
  $("#atlas-refresh").addEventListener("click", refresh);
  ["#case-search", "#dataset-filter", "#stage-filter"].forEach(id => $(id).addEventListener("input", () => { if (cohort) caseList(); }));
  document.addEventListener("click", event => {
    const row = event.target.closest("[data-case]"), baseline = event.target.closest("[data-method]"), match = event.target.closest("[data-match]");
    if (row) void choose(row.dataset.case);
    if (baseline) { method = baseline.dataset.method; summary(); caseList(); void choose(caseId); }
    if (match) { selected = Number(match.dataset.match); draw(); }
  });
  document.addEventListener("input", event => {
    if (event.target.id === "match-confidence") { minimum = Number(event.target.value); $("#confidence-value").textContent = minimum.toFixed(2); draw(); }
    if (event.target.id === "inliers-only") { inliers = event.target.checked; draw(); }
    if (event.target.id === "show-lines") { lines = event.target.checked; draw(); }
    if (event.target.id === "show-confidence") { heatmap = event.target.checked; draw(); }
    if (event.target.id === "match-color") { color = event.target.value; draw(); }
    if (event.target.id === "match-index") { selected = event.target.value === "" ? -1 : Number(event.target.value); draw(); }
  });
  void refresh();
})();
