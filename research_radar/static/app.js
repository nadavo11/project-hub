/* Research Radar: the server owns scientific records; the browser owns selection. */
(() => {
  "use strict";
  const $ = (selector, root = document) => root.querySelector(selector);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const text = (value, fallback = "Not recorded") => value == null || value === "" ? fallback : typeof value === "object" ? JSON.stringify(value) : String(value);
  const list = value => Array.isArray(value) ? value : value == null ? [] : [value];
  const short = (value, limit = 170) => { const s = text(value); return s.length > limit ? `${s.slice(0, limit)}…` : s; };
  const date = value => { if (!value) return "Time not recorded"; const d = new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); };
  const safeURL = value => { try { const u = new URL(String(value)); return ["http:", "https:"].includes(u.protocol) ? u.href : null; } catch { return null; } };
  const link = (url, label) => safeURL(url) ? `<a href="${esc(safeURL(url))}" target="_blank" rel="noopener noreferrer">${esc(label || url)} ↗</a>` : `<span class="muted">${esc(label || "Source URL not recorded")}</span>`;
  const raw = (value, label = "Inspect complete record") => `<details data-preserve="${esc(label)}"><summary>${esc(label)}</summary><pre>${esc(JSON.stringify(value ?? null, null, 2))}</pre></details>`;
  const badge = value => {
    const label = value && typeof value === "object" ? [value.status, value.verdict, value.label].find(v => typeof v === "string") || "Structured record" : text(value, "not assessed");
    return `<span class="badge ${esc(label.replace(/[^a-z]/g, ""))}">${esc(label)}</span>`;
  };
  const accessBadge = value => badge(value && typeof value === "object" ? value.read ? "Read scope recorded" : "Verification details" : value);
  const originBadge = (record, fallback = "") => badge({
    external_publication: "External publication",
    internal_hypothesis: "Internal hypothesis · not prior art",
    experimental_observation: "Experimental observation · not a publication"
  }[record?.record_type || fallback] || "Origin not recorded");
  const reasonDimensions = {
    novelty: "Novelty",
    scientific_significance: "Scientific significance",
    technical_feasibility: "Technical feasibility",
    insufficient_evidence: "Insufficient evidence",
    unclassified: "Unclassified"
  };
  const reasonDimension = record => Object.hasOwn(reasonDimensions, record?.dimension) ? record.dimension : "unclassified";
  const dimensionOptions = value => Object.entries(reasonDimensions).map(([key, label]) => `<option value="${key}" ${value === key ? "selected" : ""}>${label}</option>`).join("");
  function eliminationReasons(o) {
    const normalize = r => typeof r === "object" && r !== null ? r : { reason: r };
    const reasons = list(o.elimination_reasons).map(normalize);
    const mirrored = new Set();
    const legacy = list(o.rejections).map(normalize).filter(r => {
      // Rejection mirrors can be timestamped separately from their canonical reason.
      const index = reasons.findIndex((previous, i) => !mirrored.has(i) &&
        text(previous.reason) === text(r.reason) && reasonDimension(previous) === reasonDimension(r) &&
        (previous.at === r.at || Math.abs(Date.parse(previous.at) - Date.parse(r.at)) < 1000));
      if (index < 0) return true;
      mirrored.add(index);
      return false;
    });
    return [...reasons, ...legacy];
  }
  function reasonBadges(o) {
    const dimensions = [...new Set(eliminationReasons(o).map(reasonDimension))];
    return dimensions.length ? `<div class="tags" aria-label="Recorded reason dimensions">${dimensions.map(d => `<span title="Recorded reason; may be historical">History · ${esc(reasonDimensions[d])}</span>`).join("")}</div>` : "";
  }
  function reasonHistory(o) {
    const reasons = eliminationReasons(o);
    if (!reasons.length) return "";
    return `<details class="panel space-bottom" data-preserve="elimination-history-${esc(o.id)}"><summary>Elimination & deferral history · ${reasons.length}</summary><div class="panel-body"><p class="hint">History is retained when a candidate is reopened. These are recorded reasons, not necessarily current blockers. Missing categories remain unclassified.</p>${reasons.map((r, i) => `<article class="decision">${badge(reasonDimensions[reasonDimension(r)])}<p>${esc(text(r.reason, "Reason not recorded"))}</p><p class="hint">${esc([date(r.at), r.by && `By ${text(r.by)}`, r.stage && `Stage: ${text(r.stage)}`].filter(Boolean).join(" · "))}</p>${r.evidence ? evidenceCards(r.evidence) : ""}${r.paper_ids || r.paper_id ? `<div class="actions">${paperButtons(r.paper_ids || r.paper_id)}</div>` : ""}${r.source_url || r.url ? link(r.source_url || r.url, "Reason source") : ""}${r.sources || r.source_refs || r.references ? section("Source references", r.sources || r.source_refs || r.references) : ""}${raw(r, `Inspect reason record · ${i + 1}`)}</article>`).join("")}</div></details>`;
  }
  const priorityLabel = value => {
    if (value && typeof value === "object") return value.rank != null ? `rank ${text(value.rank)}` : "structured judgment";
    return text(value, "not set");
  };
  const button = (label, action, attrs = "", cls = "") => `<button class="button ${cls}" data-action="${action}" ${attrs}>${label}</button>`;
  const empty = (title, description, action = "") => `<div class="empty"><div class="empty-mark" aria-hidden="true">◇</div><h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
  const section = (title, value, fallback) => `<section class="section"><h3>${esc(title)}</h3>${rich(value, fallback)}</section>`;
  const fact = (title, value, fallback) => `<div class="fact"><dt>${esc(title)}</dt><dd>${esc(text(value, fallback))}</dd></div>`;
  const panel = (title, body, extra = "", cls = "") => `<section class="panel ${cls}"><div class="panel-head"><h2>${esc(title)}</h2>${extra}</div><div class="panel-body">${body}</div></section>`;
  const icons = {
    observatory: '<circle cx="12" cy="12" r="8"/><path d="M12 4v8l6-6M4 12h3m5 5v3"/><circle cx="16" cy="8" r="1"/>',
    library: '<path d="M4 4h4v16H4zm7 0h4v16h-4zm7 1 3-1 4 15-3 1z"/>',
    tensions: '<path d="m3 5 6 6-6 6m18-12-6 6 6 6M9 11h6"/>',
    board: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="10" rx="1"/><rect x="17" y="4" width="5" height="13" rx="1"/>',
    validation: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
    methodology: '<rect x="8" y="2" width="8" height="5" rx="1"/><path d="M12 7v4M5 11h14M5 11v5m14-5v5"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/>'
  };
  const views = { observatory: "Observatory", library: "Paper library", tensions: "Scientific tensions", board: "Opportunity board", validation: "Validation lab", methodology: "Methodology" };
  const statuses = ["newly proposed", "awaiting evidence", "novelty audit", "reviewer assessment", "experiment ready", "experimenting", "promising", "rejected", "deferred"];
  const ui = {
    view: Object.hasOwn(views, location.hash.slice(1)) ? location.hash.slice(1) : "observatory",
    campaign: new URLSearchParams(location.search).get("campaign") || "",
    paper: "", tension: "", job: "", opportunity: "", validation: "", candidateTab: "Evidence",
    compare: new Set(), comparing: false, method: "retrieve", foundation: "", filters: {}, sort: "priority",
    boardQuery: "", boardStatus: "", boardDimension: "", traceQuery: "", lastSnapshot: "", loaded: false, refreshing: false,
    mutation: false, rendered: false, dirty: false
  };
  let state = { campaigns: [], papers: [], tensions: [], opportunities: [], jobs: [], events: [], validations: [], decisions: [], methodology: [], foundations: [], costs: {} };
  let toastTimer;
  const campaign = () => typeof state.campaign === "object" && state.campaign !== null ? state.campaign : state.campaigns.find(c => c.id === (ui.campaign || state.campaign)) || null;
  const selected = (type, id) => list(state[type]).find(item => String(item.id) === String(id));
  const ids = value => list(value).map(v => typeof v === "object" ? v.id || v.paper_id : v);
  const heading = (eyebrow, title, description, actions = "") => `<div class="page-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div><div class="actions">${actions}</div></div>`;

  function rich(value, fallback = "Not recorded. This remains an evidence gap.", depth = 0) {
    if (value == null || value === "" || (Array.isArray(value) && !value.length)) return `<p class="hint">${esc(fallback)}</p>`;
    if (Array.isArray(value)) return `<ul>${value.map(item => `<li>${typeof item === "object" ? rich(item, fallback, depth + 1) : esc(item)}</li>`).join("")}</ul>`;
    if (typeof value === "object") {
      if (typeof value.url === "string" && Object.keys(value).every(key => ["url", "label"].includes(key))) {
        return `<p>${link(value.url, value.label)}</p>`;
      }
      if (depth >= 2 || Object.keys(value).length > 16) return raw(value, "Inspect structured evidence");
      return `<dl class="record-fields">${Object.entries(value).map(([key, item]) => `<div><dt>${esc(key.replaceAll("_", " "))}</dt><dd>${rich(item, fallback, depth + 1)}</dd></div>`).join("")}</dl>`;
    }
    return `<p>${esc(value)}</p>`;
  }

  function showError(message) {
    const element = $("#error");
    element.hidden = !message;
    element.innerHTML = message ? `<p>${esc(message)}</p>${button("Retry", "refresh", "", "small")}` : "";
  }

  function toast(message) {
    $("#toast").textContent = message;
    $("#toast").hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $("#toast").hidden = true; }, 5000);
  }

  async function request(path, body) {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin", cache: "no-store",
      headers: body === undefined ? { Accept: "application/json" } : { Accept: "application/json", "Content-Type": "application/json" },
      ...(body === undefined ? {} : { body: JSON.stringify(body) })
    });
    const content = await response.text();
    let data;
    try { data = content ? JSON.parse(content) : {}; } catch { throw new Error(`The server returned an unreadable response (HTTP ${response.status}).`); }
    if (!response.ok) throw new Error(text(data.error || data.detail, `Request failed (HTTP ${response.status}).`));
    return data;
  }

  async function refresh(force = false) {
    if (ui.refreshing) return;
    ui.refreshing = true;
    const requestedCampaign = ui.campaign;
    try {
      const data = await request(`/api/state${requestedCampaign ? `?campaign=${encodeURIComponent(requestedCampaign)}` : ""}`);
      if (requestedCampaign !== ui.campaign) return;
      if (!Array.isArray(data.campaigns)) throw new Error("The state endpoint did not return a campaign collection.");
      const fingerprint = JSON.stringify(data);
      state = { ...state, ...data };
      for (const key of ["papers", "tensions", "opportunities", "jobs", "events", "validations", "decisions", "methodology", "foundations"]) state[key] = list(data[key]);
      if (!ui.campaign && data.campaign) ui.campaign = typeof data.campaign === "object" ? data.campaign.id : data.campaign;
      ui.loaded = true;
      $("#connection").textContent = "State synchronized";
      $("#connection").className = "connection connected";
      showError("");
      const changed = fingerprint !== ui.lastSnapshot;
      ui.lastSnapshot = fingerprint;
      if (force || changed || !ui.rendered) {
        ui.dirty = true;
        if (force || !editing()) render();
      }
      updateChrome();
    } catch (error) {
      $("#connection").textContent = "Connection interrupted";
      $("#connection").className = "connection offline";
      showError(`${error.message}${ui.loaded ? " Previously loaded records remain visible and may be stale." : " No research data has been loaded."}`);
      if (!ui.loaded) {
        $("#workspace").innerHTML = empty("The workbench could not connect", "Your research records have not been replaced. Retry after the backend is available.", button("Try again", "refresh", "", "primary"));
        $("#workspace").setAttribute("aria-busy", "false");
      }
    } finally { ui.refreshing = false; }
  }

  function editing() {
    return $("#modal").open || Boolean(document.activeElement?.closest("input,textarea,select,form"));
  }

  function updateChrome() {
    const c = campaign();
    const select = $("#campaign-select");
    const options = state.campaigns.length ? state.campaigns.map(item => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join("") : '<option value="">No campaigns yet</option>';
    if (select.innerHTML !== options && document.activeElement !== select) select.innerHTML = options;
    select.value = c?.id || ui.campaign;
    const navigation = Object.entries(views).map(([key, title]) => {
      const count = { library: state.papers.length, tensions: state.tensions.length, board: state.opportunities.length, validation: state.validations.length }[key];
      return `<button class="nav-item" data-view="${key}" ${ui.view === key ? 'aria-current="page"' : ""}><svg viewBox="0 0 26 24" aria-hidden="true">${icons[key]}</svg><span>${title}</span>${count === undefined ? "" : `<span class="nav-count">${count}</span>`}</button>`;
    }).join("") + '<a class="nav-item" href="/atlas.html"><svg viewBox="0 0 26 24" aria-hidden="true"><rect x="3" y="4" width="8" height="15"/><rect x="15" y="4" width="8" height="15"/><path d="m7 9 12 5M7 15l12-6"/></svg><span>Failure Atlas</span></a>';
    if (ui.navigation !== navigation) { $("#navigation").innerHTML = navigation; ui.navigation = navigation; }
    $("#breadcrumb").textContent = ui.opportunity && ui.view === "board" ? "Opportunity / Deep dive" : views[ui.view];
    $("#campaign-status").textContent = c ? `${c.name} · ${text(c.status)} · ${text(c.stage, "stage not recorded")}` : "No active research campaign";
    const costs = state.costs || {};
    $("#cost-summary").textContent = `HTTP ${measured(costs.http_requests)} · API ${measured(costs.api_cost_usd, "$")} · GPU ${measured(costs.gpu_hours, "", " h")}`;
  }

  function measured(value, prefix = "", suffix = "") {
    return typeof value === "number" && Number.isFinite(value) ? `${prefix}${Number.isInteger(value) ? value : value.toFixed(2)}${suffix}` : "not measured";
  }

  function render() {
    const root = $("#workspace");
    const drafts = ui.renderedCampaign === campaign()?.id ? [...root.querySelectorAll("form")].map(form => ({
      id: form.id, entity: form.dataset.id,
      fields: [...form.elements].filter(el => el.name).map(el => [el.name, el.value])
    })) : [];
    const open = new Set([...root.querySelectorAll("details[open]")].map(el => el.dataset.preserve));
    const scroll = [...root.querySelectorAll(".board,.trace-list,.table-wrap")].map(el => [el.className, el.scrollLeft, el.scrollTop]);
    const active = document.activeElement;
    const focus = active && root.contains(active) ? { id: active.id, action: active.dataset.action, entity: active.dataset.id } : null;
    const bodies = { observatory, library, tensions, board, validation, methodology };
    root.innerHTML = bodies[ui.view]();
    for (const draft of drafts) {
      const form = document.getElementById(draft.id);
      if (!form || form.dataset.id !== draft.entity) continue;
      for (const [name, value] of draft.fields) if (form.elements.namedItem(name)) form.elements.namedItem(name).value = value;
      if (form.id === "decision-form") updateDecisionFields();
    }
    root.setAttribute("aria-busy", "false");
    for (const el of root.querySelectorAll("details")) if (open.has(el.dataset.preserve)) el.open = true;
    for (const [cls, left, top] of scroll) { const el = [...root.querySelectorAll(".board,.trace-list,.table-wrap")].find(node => node.className === cls); if (el) { el.scrollLeft = left; el.scrollTop = top; } }
    if (focus) {
      const el = focus.id ? document.getElementById(focus.id) : [...root.querySelectorAll("[data-action]")].find(node => node.dataset.action === focus.action && node.dataset.id === focus.entity);
      el?.focus({ preventScroll: true });
    }
    ui.rendered = true;
    ui.renderedCampaign = campaign()?.id;
    ui.dirty = false;
    updateChrome();
  }

  function noCampaign() {
    return `<section class="panel welcome"><div class="empty-mark" aria-hidden="true">⌖</div><span class="eyebrow">A RESEARCH ENVIRONMENT, NOT AN ANSWER MACHINE</span><h2 class="space-top">Find the question worth<br>an experiment.</h2><p>Build a traceable path from literature to scientific tension, from a falsifiable hypothesis to a deliberate research decision.</p>${button("＋ Create a research campaign", "new-campaign", "", "primary")}<div class="welcome-steps"><div><span>01 / MAP THE EVIDENCE</span><h3>Start with a bounded question</h3><p>Define sources, scope, and resource limits. Inspect what is actually retrieved.</p></div><div><span>02 / CHALLENGE THE IDEA</span><h3>Separate novelty from resemblance</h3><p>Compare prior art, surface missing evidence, and record reasons to reject.</p></div><div><span>03 / DESIGN THE TEST</span><h3>Make failure informative</h3><p>Specify baselines and falsification criteria. Authorization does not run compute.</p></div></div></section>`;
  }

  function campaignActions() {
    const c = campaign();
    if (!c) return "";
    const actions = [button("Configure", "configure", c.status === "running" ? 'disabled title="Pause the campaign before configuring"' : "")];
    if (["draft", "created", "idle", "waiting", "completed", "failed"].includes(c.status)) actions.push(button("▷ Start research", "campaign-start", "", "primary"));
    if (["running", "queued", "starting"].includes(c.status)) actions.push(button("Ⅱ Pause", "campaign-pause"));
    if (c.status === "paused") actions.push(button("▷ Resume", "campaign-resume", "", "primary"));
    if (["running", "queued", "paused", "starting"].includes(c.status)) actions.push(button("Cancel", "campaign-cancel", "", "danger"));
    return actions.join("");
  }

  function observatory() {
    const c = campaign();
    const title = heading("RESEARCH OPERATIONS", "Campaign observatory", "Follow actual work, inspect its evidence, and intervene when a line of inquiry needs to change.", campaignActions());
    if (!c) return title + noCampaign();
    const config = c.config || {};
    const j = selected("jobs", ui.job);
    const stages = [["retrieve", "Literature retrieval"], ["extract", "Evidence extraction"], ["synthesize", "Tensions & hypotheses"], ["review", "Audit & review"]];
    const traces = state.events.filter(e => !ui.traceQuery || JSON.stringify(e).toLowerCase().includes(ui.traceQuery.toLowerCase())).sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")) || Number(b.id) - Number(a.id));
    return title + `<div class="notice"><strong>Model-generated analysis is provisional.</strong> Role outputs are inferences from supplied source material, not independently verified findings. Inspect claim-level evidence and verification labels before relying on them.</div><div class="split"><div class="stack"><section class="panel"><div class="panel-head"><div><span class="eyebrow">CURRENT CAMPAIGN</span><h2>${esc(c.name)}</h2></div>${badge(c.status)}</div><div class="research-question"><span class="eyebrow">${esc(c.field || "Research scope")}</span><h2>${esc(config.question || "Research question has not been specified")}</h2><p>${esc(list(config.queries).join(" · ") || "No retrieval queries configured.")}</p></div><div class="stages">${stages.map(([key, name], i) => `<div class="stage ${String(c.stage).toLowerCase().includes(key) ? "active" : ""}"><span>0${i + 1}</span><strong>${name}</strong></div>`).join("")}</div><div class="panel-body no-top"><p class="hint">Reported stage: ${esc(text(c.stage))}. This diagram describes the process; it does not simulate agent progress.</p></div></section>
      <section class="panel"><div class="panel-head"><h2>Agent work queue</h2><span class="hint">${state.jobs.length} persisted tasks</span></div>${state.jobs.length ? `<div class="table-wrap"><table><thead><tr><th>Agent / task</th><th>Status</th><th>Updated</th><th>Control</th></tr></thead><tbody>${state.jobs.map(job => `<tr class="${ui.job === job.id ? "selected" : ""}"><td><button class="text-button title-link" data-action="inspect-job" data-id="${esc(job.id)}">${esc(job.role || job.kind || "Research task")}</button><p class="hint">${esc(short(job.input?.query || job.kind || job.id, 80))}</p></td><td>${badge(job.status)}</td><td class="mono dim">${esc(date(job.updated_at || job.created_at))}</td><td><div class="actions">${jobControls(job)}</div></td></tr>`).join("")}</tbody></table></div>` : empty("No tasks have been queued", "Start the campaign to retrieve literature. Every task shown here will be backed by a persisted record.")}</section>
      ${j ? panel("Task inspector", `<div class="row-top"><span class="mono">${esc(j.id)}</span>${badge(j.status)}</div>${section("Input", j.input)}${section("Output", j.output, "No output has been recorded.")}${j.error ? `<div class="notice warning">${esc(text(j.error))}</div>` : ""}${raw(j)}`, button("Close", "close-job", "", "small")) : ""}
      <section class="panel"><div class="panel-head"><h2>Execution trace</h2><span class="hint">Persisted events · newest first</span></div><div class="panel-body no-bottom"><label class="field">Filter trace<input id="trace-search" data-filter="trace" type="search" placeholder="Search events, task IDs, or sources…" value="${esc(ui.traceQuery)}"></label></div>${traces.length ? `<div class="trace-list">${traces.map(e => `<article class="trace"><div class="trace-meta"><time>${esc(date(e.created_at))}</time><span>${esc(e.kind || "event")}</span></div><p>${esc(e.message || "Event record")}</p>${raw(e, `Raw event · ${e.id}`)}</article>`).join("")}</div>` : empty(ui.traceQuery ? "No matching events" : "No execution trace yet", ui.traceQuery ? "Try a different search term." : "Actual retrieval, extraction, and review events appear here as work is recorded.")}</section></div>
      <aside class="stack">${panel("Research controls", `<form id="investigate-form"><label class="field">Follow a specific lead<textarea name="query" required maxlength="1000" placeholder="A mechanism, conflicting result, or missing baseline…"></textarea></label><p class="hint space-top">Queues a real literature search within this campaign’s bounds.</p><button class="button cyan full-width space-top">Investigate this direction</button></form>`)}
      ${costPanel()}
      ${panel("Campaign boundaries", `<dl class="facts">${fact("Paper limit", config.max_papers)}${fact("Request limit", config.max_requests)}${fact("Time budget", config.time_budget_seconds == null ? null : `${config.time_budget_seconds} s`)}${fact("API budget", config.api_budget_usd == null ? null : `$${config.api_budget_usd}`)}${fact("Compute budget", config.compute_budget_hours == null ? null : `${config.compute_budget_hours} GPU h`)}${fact("Venues", list(config.venues).join(", "))}</dl>${raw(config, "Inspect complete configuration")}`)}
      ${panel("Research artifacts", `<p class="hint">Export the evidence, decisions, and provenance stored for this campaign.</p><div class="actions space-top"><a class="button small" href="/api/export?campaign=${encodeURIComponent(c.id)}" download>Export JSON ↗</a><a class="button small" href="/api/report?campaign=${encodeURIComponent(c.id)}" download>Research report ↗</a></div>`)}</aside></div>`;
  }

  function costPanel() {
    const c = state.costs || {};
    const receipts = [["CLI requests", "cli_requests"], ["CLI usage · nano-AIU", "cli_nano_aiu"], ["Model input tokens", "model_input_tokens"], ["Model output tokens", "model_output_tokens"]];
    return panel("Observed resource use", `<dl class="facts costs">${fact("HTTP requests", measured(c.http_requests))}${fact("Downloaded", c.download_bytes == null ? "not measured" : `${(c.download_bytes / 1048576).toFixed(2)} MB`)}${fact("Elapsed", measured(c.elapsed_seconds, "", " s"))}${fact("API cost", measured(c.api_cost_usd, "$"))}${fact("GPU hours", measured(c.gpu_hours))}${receipts.filter(([, key]) => Object.hasOwn(c, key)).map(([label, key]) => fact(label, measured(c[key]))).join("")}</dl><p class="hint">Unknown cost is not zero. Authorization records permission only; this workbench has no GPU execution runner.</p>${c.note ? `<p class="hint space-top">${esc(c.note)}</p>` : ""}${raw(c, "Inspect measured cost receipts")}`);
  }

  function jobControls(job) {
    if (campaign()?.status === "cancelled" || ["completed", "cancelled"].includes(job.status)) return '<span class="hint">Recorded</span>';
    const attr = `data-id="${esc(job.id)}"`;
    const controllable = ["failed", "paused", "interrupted", "waiting"].includes(job.status);
    return (["failed", "interrupted", "waiting"].includes(job.status) ? button("Retry", "job-retry", attr, "small") : "") +
      (job.status === "paused" ? button("Resume", "job-resume", attr, "small") : ["running", "queued"].includes(job.status) ? button("Pause", "job-pause", attr, "small") : "") +
      button("Redirect", "job-redirect", `${attr} ${controllable ? "" : 'disabled title="Pause the task before redirecting it"'}`, "small subtle");
  }

  function filterOptions(key, label) {
    const values = [...new Set(state.papers.flatMap(p => key === "family" ? paperFamilies(p) : list(p[key]).map(v => text(v, "")).filter(Boolean)))].sort();
    return `<label>${label}<select data-library-filter="${key}" id="filter-${key}"><option value="">All ${label.toLowerCase()}s</option>${values.map(v => `<option ${ui.filters[key] === v ? "selected" : ""} value="${esc(v)}">${esc(v)}</option>`).join("")}</select></label>`;
  }

  function filteredPapers() {
    return state.papers.filter(p => {
      const f = ui.filters;
      if (f.query && !JSON.stringify(p).toLowerCase().includes(f.query.toLowerCase())) return false;
      for (const key of ["venue", "task", "family", "datasets", "relevance"]) if (f[key] && !(key === "family" ? paperFamilies(p) : list(p[key])).some(v => text(v) === f[key])) return false;
      const published = p.date || (p.year ? `${p.year}-01-01` : "");
      if ((f.from || f.to) && !published) return false;
      if (f.from && published < f.from) return false;
      if (f.to && String(published).slice(0, 10) > f.to) return false;
      return true;
    });
  }

  function library() {
    const papers = filteredPapers();
    const p = selected("papers", ui.paper);
    return heading("EVIDENCE COLLECTION", "Paper library", "Read the mechanism, limitations, and source evidence—not just the abstract.") + landscape() +
      `<div class="toolbar"><label class="search">Search the evidence store<input id="library-search" type="search" data-library-filter="query" placeholder="Title, author, claim, dataset…" value="${esc(ui.filters.query || "")}"></label><label class="filter-date">Published from<input id="filter-from" type="date" data-library-filter="from" value="${esc(ui.filters.from || "")}"></label><label class="filter-date">Published through<input id="filter-to" type="date" data-library-filter="to" value="${esc(ui.filters.to || "")}"></label>${button("Clear filters", "clear-filters", "", "subtle")}</div>
      <div class="filter-panel"><div class="toolbar">${filterOptions("venue", "Venue")}${filterOptions("task", "Task")}${filterOptions("family", "Family")}${filterOptions("datasets", "Dataset")}${filterOptions("relevance", "Relevance")}</div></div><p class="result-count">${papers.length} of ${state.papers.length} papers · undated papers are excluded when a date filter is active</p>
      <div class="split wide"><section class="panel">${papers.length ? papers.map(item => `<button class="paper-row" data-action="inspect-paper" data-id="${esc(item.id)}" aria-pressed="${ui.paper === item.id}"><div class="row-top"><span class="mono">${esc(item.year || item.date || "UNDATED")} · ${esc(text(item.venue, "Venue unverified"))}</span>${accessBadge(item.verification)}</div><h3>${esc(item.title)}</h3>${originBadge(item, "external_publication")}<p>${esc(short(list(item.authors).map(a => typeof a === "object" ? a.name : a).join(", "), 115))}</p><div class="tags">${list(item.family).concat(list(item.task), list(item.datasets)).slice(0, 5).map(tag => `<span>${esc(text(tag))}</span>`).join("")}</div></button>`).join("") : empty(state.papers.length ? "No papers match these filters" : "The evidence store is empty", state.papers.length ? "Broaden the filters to see more sources." : "Start a campaign or investigate a direction. Retrieved papers and their provenance will appear here.")}</section><aside class="panel sticky" id="paper-inspector">${p ? paperInspector(p) : empty("Select a paper to inspect", "Source evidence, extracted mechanisms, and evaluation limits stay beside the library.")}</aside></div>`;
  }

  function paperFamilies(paper) {
    const values = list(paper.family).map(value => text(value, "").trim()).filter(Boolean);
    return [...new Set(values.length ? values : ["Not classified"])];
  }

  function landscape() {
    const groups = new Map();
    for (const paper of state.papers) {
      for (const family of paperFamilies(paper)) groups.set(family, [...(groups.get(family) || []), paper]);
    }
    return `<details class="panel landscape" data-preserve="method-landscape"><summary>Method landscape <span class="hint">Actual family, task, dataset & evaluation relationships · ${state.papers.length} papers</span></summary>${state.papers.length ? `<div class="panel-body"><p class="hint">Classification reflects stored source records, not measured similarity or benchmark comparability. Select a family to filter the library; select a paper to inspect its evidence.</p><div class="family-taxonomy">${[...groups].sort(([a], [b]) => a.localeCompare(b)).map(([family, papers]) => `<button class="family-chip" data-action="filter-family" data-family="${esc(family)}" aria-pressed="${ui.filters.family === family}"><span>${esc(family)}</span><strong>${papers.length}</strong></button>`).join("")}</div><div class="table-wrap landscape-table" tabindex="0" aria-label="Method landscape relationships"><table><thead><tr><th>Family</th><th>Paper</th><th>Task</th><th>Datasets</th><th>Evaluation</th></tr></thead><tbody>${state.papers.map(p => `<tr><td>${paperFamilies(p).map(f => `<button class="text-button" data-action="filter-family" data-family="${esc(f)}">${esc(f)}</button>`).join("<br>")}</td><td><button class="text-button title-link" data-action="landscape-paper" data-id="${esc(p.id)}">${esc(p.title)}</button></td><td>${esc(text(p.task, "Task not recorded"))}</td><td>${esc(list(p.datasets).map(v => text(v)).join(", ") || "Datasets not recorded")}</td><td>${esc(short(p.evaluation || "Evaluation not recorded", 220))}</td></tr>`).join("")}</tbody></table></div></div>` : empty("No method landscape yet", "Family relationships appear only after actual paper records are available. No taxonomy or benchmark scores are invented.")}</details>`;
  }

  function evidenceCards(evidence, origin = "") {
    if (!list(evidence).length) return `<p class="hint">No claim-level evidence has been recorded. Do not treat this as verified support.</p>`;
    return list(evidence).map(e => {
      if (typeof e !== "object" || e === null) return `<div class="evidence">${esc(e)}</div>`;
      const source = selected("papers", e.paper_id);
      return `<article class="evidence"><div class="row-top">${originBadge(e, source?.record_type || origin)}${badge(e.level || "evidence level unspecified")}${badge(e.verified === true ? "source checked" : e.verified === false ? "source unchecked" : "verification unknown")}</div>${rich(e.claim || e.observation, "Claim not recorded")}${e.quote ? `<blockquote>${esc(text(e.quote))}</blockquote>` : ""}<footer>${link(e.source_url || e.url, "Open source")}<span>${esc(text(e.location, "Location not recorded"))}</span></footer>${e.paper_id ? paperButtons(e.paper_id) : ""}${raw(e, "Inspect evidence record")}</article>`;
    }).join("");
  }

  function paperInspector(p) {
    const url = p.url || (p.doi ? `https://doi.org/${p.doi}` : p.arxiv_id ? `https://arxiv.org/abs/${p.arxiv_id}` : null);
    const authors = list(p.authors).map(a => typeof a === "object" ? a.name : a);
    const authorSummary = authors.slice(0, 6).join(", ") + (authors.length > 6 ? ` · +${authors.length - 6} authors` : "");
    return `<div class="panel-head"><h2>Paper inspector</h2>${button("Close", "close-paper", "", "small subtle")}</div><div class="panel-body"><span class="eyebrow">${esc(text(p.family, "Method family not classified"))}</span><h2 class="inspector-title">${esc(p.title)}</h2>${originBadge(p, "external_publication")}<p class="hint">${esc(authorSummary || "Authors not recorded")}</p>${authors.length > 6 ? raw(authors, `Show all ${authors.length} authors`) : ""}<div class="actions source-actions">${link(url, "Read paper")}${accessBadge(p.verification)}</div><p class="notice">Source access is not independent scientific verification or reproduction. “Full paper” describes the evidence source, not a complete audit; inspect the recorded read scope.</p>${p.verification && typeof p.verification === "object" ? section("Source access & verification", p.verification) : ""}${section("Contribution", p.contribution)}${section("Mechanism", p.mechanism)}${section("Evaluation & datasets", p.evaluation || p.datasets)}${section("Limitations", p.limitations)}<section class="section"><h3>Claim-level provenance</h3>${evidenceCards(p.evidence, p.record_type || "external_publication")}</section>${raw(p)}</div>`;
  }

  function paperButtons(paperIds) {
    return ids(paperIds).map(id => { const p = selected("papers", id); return `<span>${originBadge(p, p ? "external_publication" : "")} <button class="text-button" data-action="open-paper" data-id="${esc(id)}">${esc(p?.title || id)} ↗</button></span>`; }).join("<br>");
  }

  function tensions() {
    const t = selected("tensions", ui.tension);
    return heading("SYNTHESIS / UNRESOLVED QUESTIONS", "Scientific tensions", "Follow disagreements, missing controls, and competing explanations into testable directions.") +
      `<div class="split wide"><section class="panel">${state.tensions.length ? state.tensions.map(item => `<button class="tension-row" data-action="inspect-tension" data-id="${esc(item.id)}" aria-pressed="${ui.tension === item.id}"><div class="row-top"><span class="mono">${esc(item.id)}</span><span class="badge cyan">${list(item.paper_ids).length} linked sources</span></div><h3>${esc(item.title)}</h3><p>${esc(short(item.observation))}</p><div class="tags"><span>${list(item.opportunity_ids).length || state.opportunities.filter(o => ids(o.tension_ids).includes(item.id)).length} research directions</span></div></button>`).join("") : empty("No scientific tensions recorded", "Tensions emerge from retrieved evidence. A lack of agreement is not automatically a contradiction.")}</section><aside class="panel sticky">${t ? `<div class="panel-head"><h2>Tension inspector</h2>${button("Close", "close-tension", "", "small")}</div><div class="panel-body"><h2 class="inspector-title">${esc(t.title)}</h2>${section("Observation", t.observation)}<section class="section"><h3>Supporting and conflicting evidence</h3>${evidenceCards(t.evidence)}<div class="actions">${paperButtons(t.paper_ids)}</div></section>${section("Competing explanations", t.explanations)}${section("What remains unresolved", t.unresolved)}${section("Possible directions", t.directions)}<section class="section"><h3>Related opportunities</h3>${state.opportunities.filter(o => ids(t.opportunity_ids).includes(o.id) || ids(o.tension_ids).includes(t.id)).map(o => `<p><button class="text-button" data-action="open-opportunity" data-id="${esc(o.id)}">${esc(o.title)} ↗</button></p>`).join("") || '<p class="hint">No linked candidates yet.</p>'}</section>${raw(t)}</div>` : empty("Select a tension", "Inspect the observation, alternative explanations, and evidence before promoting a hypothesis.")}</aside></div>`;
  }

  function sortedCandidates() {
    const priority = (a, b) => {
      if (typeof a === "number" || typeof b === "number") return (typeof b === "number" ? b : -1) - (typeof a === "number" ? a : -1);
      if (typeof a?.rank === "number" || typeof b?.rank === "number") return (a?.rank ?? Infinity) - (b?.rank ?? Infinity);
      const levels = { high: 3, medium: 2, low: 1 };
      return (levels[String(b).toLowerCase()] || 0) - (levels[String(a).toLowerCase()] || 0);
    };
    return state.opportunities.filter(o => (!ui.boardQuery || JSON.stringify(o).toLowerCase().includes(ui.boardQuery.toLowerCase())) && (!ui.boardStatus || o.status === ui.boardStatus) && (!ui.boardDimension || eliminationReasons(o).some(r => reasonDimension(r) === ui.boardDimension))).sort((a, b) => ui.sort === "title" ? String(a.title).localeCompare(String(b.title)) : ui.sort === "updated" ? String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")) : priority(a.priority, b.priority));
  }

  function board() {
    const candidate = selected("opportunities", ui.opportunity);
    if (candidate) return opportunity(candidate);
    if (ui.comparing) return compareView();
    const items = sortedCandidates();
    const unknown = items.filter(o => !statuses.includes(o.status));
    const lanes = unknown.length ? [...statuses, "unclassified"] : statuses;
    return heading("HYPOTHESES / DECISION WORKSPACE", "Opportunity board", "Track scientific readiness—not a synthetic score. Open a candidate to challenge the evidence.", button("Investigate a new direction", "investigate", "", "cyan")) +
      `<div class="toolbar"><label class="search">Find a candidate<input id="board-search" data-filter="board" type="search" placeholder="Hypothesis, mechanism, or limitation…" value="${esc(ui.boardQuery)}"></label><label>Status<select id="board-status"><option value="">All nine stages</option>${statuses.map(s => `<option ${ui.boardStatus === s ? "selected" : ""}>${s}</option>`).join("")}</select></label><label>Reason dimension · includes history<select id="board-dimension"><option value="">All reason dimensions</option>${dimensionOptions(ui.boardDimension)}</select></label><label>Sort within stages<select id="board-sort"><option value="priority" ${ui.sort === "priority" ? "selected" : ""}>Priority</option><option value="updated" ${ui.sort === "updated" ? "selected" : ""}>Recently updated</option><option value="title" ${ui.sort === "title" ? "selected" : ""}>Title</option></select></label></div>
      ${ui.compare.size ? `<div class="compare-tray"><span>${ui.compare.size} selected · compare 2–3 candidates on the same scientific criteria</span><div class="actions">${button("Clear", "clear-compare", "", "small subtle")}${button("Compare candidates →", "compare", ui.compare.size < 2 ? "disabled" : "", "small primary")}</div></div>` : '<p class="result-count">Select 2–3 candidates for side-by-side comparison. Scroll horizontally to inspect all stages.</p>'}
      ${!state.opportunities.length ? '<div class="notice"><strong>No hypotheses yet.</strong> The board is an empty research structure, not seeded findings. Start a campaign to build evidence-backed candidates.</div>' : ""}
      <div class="board" tabindex="0" aria-label="Opportunity stages, horizontally scrollable">${lanes.map(status => { const cards = items.filter(o => status === "unclassified" ? !statuses.includes(o.status) : o.status === status); return `<section class="board-lane"><div class="lane-head"><h2>${esc(status[0].toUpperCase() + status.slice(1))}</h2><span>${cards.length}</span></div><div class="lane-body">${cards.length ? cards.map(o => `<article class="candidate"><div class="row-top"><span class="mono dim">${esc(String(o.id).slice(0, 12))}</span><label class="check"><input type="checkbox" data-compare="${esc(o.id)}" ${ui.compare.has(o.id) ? "checked" : ""} aria-label="Compare ${esc(o.title)}">Compare</label></div><h3><button class="text-button title-link" data-action="open-opportunity" data-id="${esc(o.id)}">${esc(o.title)}</button></h3>${originBadge(o, "internal_hypothesis")}<p>${esc(short(o.hypothesis || o.question))}</p>${reasonBadges(o)}<div class="candidate-footer"><span>Priority: ${esc(priorityLabel(o.priority))}</span><button class="text-button" data-action="open-opportunity" data-id="${esc(o.id)}">Inspect →</button></div></article>`).join("") : '<div class="lane-empty">No matching candidates in this stage</div>'}</div></section>`; }).join("")}</div>`;
  }

  function opportunity(o) {
    const tabs = ["Evidence", "Prior art", "Review", "Experiment", "Decisions"];
    const linkedPapers = new Set([...ids(o.paper_ids), ...list(o.prior_art).map(p => p.paper_id), ...state.tensions.filter(t => ids(o.tension_ids).includes(t.id)).flatMap(t => ids(t.paper_ids))]);
    let body;
    if (ui.candidateTab === "Evidence") body = `${section("Falsifiable hypothesis", o.hypothesis)}${section("Proposed contribution", o.contribution)}${section("Why this could matter", o.significance)}${o.priority && typeof o.priority === "object" ? section("Priority judgment and rationale", o.priority) : ""}<section class="section"><h3>Evidence and provenance</h3>${evidenceCards(o.evidence)}${[...linkedPapers].map(id => { const p = selected("papers", id); return p ? `<article class="evidence">${originBadge(p, "external_publication")}<button class="text-button title-link" data-action="open-paper" data-id="${esc(p.id)}">${esc(p.title)} ↗</button><p>${esc(short(p.contribution, 300))}</p>${accessBadge(p.verification)}${evidenceCards(p.evidence, p.record_type || "external_publication")}</article>` : `<p class="hint">Source ${esc(id)} is referenced but absent from the current library.</p>`; }).join("")}</section>${section("Evidence gaps", o.gaps)}<section class="section"><h3>Originating tensions</h3>${ids(o.tension_ids).map(id => `<p><button class="text-button" data-action="open-tension" data-id="${esc(id)}">${esc(selected("tensions", id)?.title || id)} ↗</button></p>`).join("") || '<p class="hint">No originating tension linked.</p>'}</section>`;
    else if (ui.candidateTab === "Prior art") body = `${section("Novelty assessment", o.novelty, "Novelty has not been audited. Different wording does not establish a new contribution.")}${list(o.prior_art).length ? list(o.prior_art).map(prior => { const p = selected("papers", prior.paper_id); return `<section class="section"><h3>${esc(p?.title || prior.title || prior.paper_id || "Prior-art comparison")}</h3><div class="prior-art-grid"><div><span class="eyebrow">EXISTING WORK</span><div>${originBadge(p || prior, p ? "external_publication" : "")}</div><h3 class="space-top">What already exists</h3>${rich(prior.overlap || p?.contribution)}<div class="space-top">${p ? `<button class="text-button" data-action="open-paper" data-id="${esc(p.id)}">Inspect source evidence ↗</button>` : link(prior.url, "Open prior art")}</div></div><div><span class="eyebrow">PROPOSED DIFFERENCE</span><div>${originBadge(o, "internal_hypothesis")}</div><h3 class="space-top">What must be demonstrated</h3>${rich(prior.difference, "A meaningful difference has not been recorded.")}</div></div>${raw(prior, "Inspect comparison record")}</section>`; }).join("") : empty("No prior-art comparison recorded", "Challenge this candidate with a specific overlap or missing reference before treating novelty as established.")}`;
    else if (ui.candidateTab === "Review") body = `${section("Reviewer assessment", o.review, "No reviewer assessment is recorded.")}${rankingDetails(o)}${section("Known weaknesses & gaps", o.gaps)}${section("Target venue & fit", o.venue)}<div class="notice">A favorable review is not an empirical result. Inspect the assumptions and missing controls before promoting this candidate.</div>`;
    else if (ui.candidateTab === "Experiment") body = experiment(o);
    else body = decisionHistory(o);
    return `<div class="actions space-bottom">${button("← Opportunity board", "back-board", "", "subtle small")}${badge(o.status)}${originBadge(o, "internal_hypothesis")}<span class="hint">Priority: ${esc(priorityLabel(o.priority))}</span></div><div class="detail-heading"><span class="eyebrow">CANDIDATE / ${esc(o.id)}</span><h1>${esc(o.title)}</h1><p>${esc(text(o.question, "Research question not recorded."))}</p></div><div class="notice"><strong>Provisional research hypothesis.</strong> Model-generated synthesis, novelty assessments, and reviews are not independently verified results.</div>${reasonHistory(o)}<div class="tabs" role="tablist" aria-label="Candidate detail">${tabs.map(tab => `<button role="tab" id="tab-${tab.replace(" ", "-")}" aria-controls="candidate-panel" aria-selected="${ui.candidateTab === tab}" data-candidate-tab="${tab}" tabindex="${ui.candidateTab === tab ? 0 : -1}">${tab}</button>`).join("")}</div><div class="split"><section class="panel"><div class="panel-body" id="candidate-panel" role="tabpanel" aria-labelledby="tab-${ui.candidateTab.replace(" ", "-")}">${body}${raw(o)}</div></section><aside class="stack">${panel("Research judgment", decisionForm(o))}${panel("Investigation loop", `<p class="hint">Search for a missing control, challenge novelty, or pursue an alternative mechanism. The query and its task trace remain in this campaign.</p>${button("Investigate this candidate", "investigate", `data-id="${esc(o.id)}"`, "cyan full-width space-top")}`)}${panel("Decision trail", decisionHistory(o, true))}</aside></div>`;
  }

  function experiment(o) {
    const e = o.experiment || {};
    return `<div class="notice warning"><strong>Plan, not execution.</strong> Authorization records permission only. No GPU runner is attached; no training or benchmark is started by this interface.</div><div class="row-top"><h2>Minimal discriminating experiment</h2>${badge(e.status || "not planned")}</div>${section("Hypothesis under test", e.hypothesis || o.hypothesis)}${section("Datasets & splits", e.datasets)}${section("Baselines", e.baselines)}${section("Metrics", e.metrics)}${section("Configuration", e.config)}${section("Compute estimate", e.compute, "Compute has not been estimated. Do not assume zero cost.")}${section("Success criteria", e.success)}${section("Falsification criteria", e.falsification)}${section("Authorization", e.authorization, "No explicit authorization recorded.")}${e.results ? originBadge(e.results, "experimental_observation") : ""}${section("Observed results", e.results, "No execution results recorded. A plan or authorization is not an experiment.")}${e.results ? '<p class="notice warning">Researcher-supplied external results are independently unverified. Inspect the artifact and protocol; recording measurements is not validation.</p>' : ""}<div class="actions">${button("Record experiment authorization", "authorize", `data-id="${esc(o.id)}"`, "cyan")}${button("Record external result", "record-result", `data-id="${esc(o.id)}" ${o.experiment ? "" : 'disabled title="An experiment plan is required"'}`)}</div>`;
  }

  function rankingDetails(o) {
    const record = list(state.ranking).find(r => r.opportunity_id === o.id);
    if (!record) return "";
    const score = typeof record.score === "number" && Number.isFinite(record.score) ? `${record.score.toFixed(2)} / 4` : "Not scored · incomplete judgments";
    return `<section class="section"><h3>Recorded weighted judgments</h3><p>${esc(score)}</p><p class="hint space-top">Ordinal research judgments, not acceptance probabilities. Missing dimensions are not scored as zero.</p>${rich(record.interpretation)}${section("Missing judgments", record.missing, "No missing dimensions reported.")}${raw(record.dimensions, "Inspect dimensions and reasons")}${raw(record.weights, "Inspect ranking weights")}</section>`;
  }

  function decisionForm(o) {
    return `<form class="decision-form" id="decision-form" data-id="${esc(o.id)}"><label class="field">Decision<select name="action" id="decision-action"><option value="comment">Add a comment</option><option value="challenge">Challenge / search counterevidence</option><option value="revise">Revise hypothesis</option><option value="prioritize">Set priority</option><option value="approve">Approve experiment planning</option><option value="defer">Defer</option><option value="reject">Reject</option><option value="reopen">Reopen</option><option value="authorize">Authorize plan only (no execution)</option></select></label><label class="field" id="dimension-field" hidden>Reason dimension<select name="dimension" id="decision-dimension" disabled><option value="">Choose a reason dimension…</option>${dimensionOptions("")}</select><span class="hint">Choose the primary blocker; use Unclassified if the evidence does not establish a category.</span></label><label class="field">Reason / research note<textarea name="reason" required placeholder="What evidence supports this decision?"></textarea></label><label class="field" id="revision-field" hidden>Revised hypothesis<textarea name="hypothesis" placeholder="State a testable alternative…">${esc(o.hypothesis || "")}</textarea></label><label class="field" id="priority-field" hidden>Priority<input type="number" name="priority" min="0" max="10" step="1" value="${typeof o.priority === "number" ? o.priority : 0}"><span class="hint">0–10 human ordering preference, not a scientific confidence score.</span></label><p id="decision-warning" class="hint space-top">Reasons are saved with the candidate’s decision history.</p><button class="button primary full-width">Save research judgment</button><p class="form-error" role="alert"></p></form>`;
  }

  function updateDecisionFields() {
    const action = $("#decision-action")?.value;
    if (!action) return;
    $("#revision-field").hidden = action !== "revise";
    $("#priority-field").hidden = action !== "prioritize";
    const needsDimension = ["reject", "defer"].includes(action);
    $("#dimension-field").hidden = !needsDimension;
    $("#decision-dimension").disabled = !needsDimension;
    $("#decision-dimension").required = needsDimension;
    $("#decision-warning").textContent = action === "authorize" ? "Permission only: no experiment will be executed." : action === "challenge" ? "Your reason becomes a real counterevidence search query." : "Reasons are saved with the candidate’s decision history.";
  }

  function decisionHistory(o, compact = false) {
    const records = state.decisions.filter(d => d.opportunity_id === o.id || d.candidate_id === o.id);
    const comments = list(o.comments).filter(c => typeof c !== "object" || !records.some(d => (d.id && d.id === c.id) || (d.action === c.action && (d.reason || d.text) === (c.reason || c.text))));
    const all = [...records, ...comments.map(c => typeof c === "object" ? c : { action: "comment", reason: c })];
    const shown = compact ? all.slice(-4) : all;
    return shown.length ? shown.map(d => `<article class="decision"><div class="row-top">${badge(d.action || "comment")}${["reject", "defer"].includes(d.action) ? badge(reasonDimensions[reasonDimension(d)]) : ""}<time>${esc(date(d.created_at || d.timestamp || d.at))}</time></div><p>${esc(text(d.reason || d.text || d.comment || d.body, "Reason not recorded"))}</p>${d.hypothesis ? `<p><strong>Revised:</strong> ${esc(d.hypothesis)}</p>` : ""}${compact ? "" : raw(d, `Inspect decision · ${d.id || d.created_at || d.action}`)}</article>`).join("") : '<p class="hint">No saved judgments yet. A rejection reason is as valuable as an approval.</p>';
  }

  function compareView() {
    const items = [...ui.compare].map(id => selected("opportunities", id)).filter(Boolean);
    const criteria = [["Hypothesis", "hypothesis"], ["Contribution", "contribution"], ["Scientific significance", "significance"], ["Novelty evidence", "novelty"], ["Reviewer assessment", "review"], ["Evidence gaps", "gaps"], ["Experiment plan", "experiment"]];
    return heading("SIDE-BY-SIDE RESEARCH JUDGMENT", "Compare candidates", "Read comparable evidence and unresolved risks. There is no composite novelty score.", button("← Back to board", "back-board")) + `<div class="compare-grid columns-${Math.max(items.length, 1)}">${items.map(o => `<section class="panel"><div class="panel-body"><div class="row-top">${badge(o.status)}<span class="hint">Priority: ${esc(priorityLabel(o.priority))}</span></div><h2 class="inspector-title">${esc(o.title)}</h2>${button("Open deep dive →", "open-opportunity", `data-id="${esc(o.id)}"`, "small cyan")}${criteria.map(([label, key]) => `<section class="comparison-field"><h3>${label}</h3>${rich(o[key])}</section>`).join("")}</div></section>`).join("")}</div>`;
  }

  function validation() {
    const v = selected("validations", ui.validation) || selected("validations", "pilot-go-no-go") || state.validations[0];
    return heading("SCIENTIFIC / OPERATIONAL CHECKS", "Validation lab", "Inspect what was expected, what was observed, and whether the available evidence is sufficient.") +
      '<div class="notice"><strong>Validation is not a badge of scientific truth.</strong> Operational tests, literature checks, and experimental results have different scopes. Read each record’s limitations.</div>' +
      `<div class="split wide"><section class="panel">${state.validations.length ? state.validations.map(record => `<button class="validation-row" data-action="inspect-validation" data-id="${esc(record.id)}" aria-pressed="${v?.id === record.id}"><div class="row-top"><span class="mono">${esc(record.kind || record.id)}</span>${badge(record.verdict || record.status)}</div><h3>${esc(record.title || record.name || "Validation record")}</h3><p class="hint">${esc(short(record.summary || record.criteria || "Open the record to inspect evidence."))}</p></button>`).join("") : empty("No validation evidence available", "Actual validation records will appear here. No success rate or test result is inferred from an empty collection.")}</section><section class="panel">${v ? `<div class="panel-head"><h2>${esc(v.title || v.name || "Validation detail")}</h2>${badge(v.verdict || v.status)}</div><div class="panel-body">${section("Acceptance criteria", v.criteria || v.expected)}${section("Observed outcome", v.observed || v.summary)}${list(v.cases).map((test, i) => typeof test === "object" && test !== null ? `<section class="section"><div class="row-top"><h3>${esc(test.title || test.name || `Case ${i + 1}`)}</h3>${badge(test.verdict || test.status)}</div><div class="prior-art-grid"><div><h4>Expected</h4>${rich(test.expected || test.criteria)}</div><div><h4>Observed</h4>${rich(test.observed || test.actual)}</div></div>${section("Evidence", test.evidence)}${raw(test, `Inspect case ${i + 1}`)}</section>` : section(`Case ${i + 1}`, test)).join("")}${section("Evidence", v.evidence)}${section("Failures", v.failures, "No failure list supplied. This is not proof that all checks passed.")}${section("Limitations", v.limitations)}${raw(v, "Inspect full validation record")}</div>` : empty("Evidence before verdict", "Choose a validation run to inspect its criteria, observed results, and remaining limitations.")}</section></div>`;
  }

  const methods = {
    scope: { number: "01", title: "Bound the question", subtitle: "Scope, sources, and budgets", body: "A campaign begins with a scientific question, explicit retrieval queries, and bounded time and resource budgets. Scope is a constraint on the inquiry, not evidence that the question is important.", inputs: "Question · field · seed queries · date and venue constraints", outputs: "Persisted campaign configuration and resource limits", failure: "A question that is too broad, a missing baseline, or an exhausted retrieval budget must remain visible.", roles: ["scope", "plan"] },
    retrieve: { number: "02", title: "Retrieve & verify", subtitle: "Real sources, inspectable provenance", body: "Retrieval tasks collect actual source records. Canonical links and exact source locations are retained where available. Finding a paper does not verify its claims; metadata-only records remain limited evidence.", inputs: "Campaign queries or a researcher’s directed investigation", outputs: "Paper records · source URLs · retrieval events", failure: "Network errors and incomplete extraction are task failures, not empty proof. Retry or redirect failed work from the observatory.", roles: ["retrieve", "search", "librarian"] },
    evidence: { number: "03", title: "Evidence store", subtitle: "Claims, mechanisms, and limitations", body: "The library keeps extracted contributions, methods, evaluation conditions, quotations, and verification levels together. Unsupported fields are left unrecorded rather than filled with plausible summaries.", inputs: "Retrieved paper records and accessible text", outputs: "Claim-level evidence with source locations and verification state", failure: "Abstract-only evidence cannot establish full-paper ablations, implementation availability, or benchmark validity.", roles: ["extract", "evidence", "reader"] },
    synthesis: { number: "04", title: "Find scientific tensions", subtitle: "Conflicts → competing explanations", body: "Synthesis connects observations across papers while keeping alternative explanations visible. A difference in datasets, assumptions, or protocols may explain an apparent conflict. Candidate hypotheses should arise from these unresolved tensions.", inputs: "Verified and explicitly limited claims across papers", outputs: "Observations · explanations · open questions · linked opportunities", failure: "Correlation, changed protocols, and unsupported extrapolation are not novel mechanisms.", roles: ["synth", "tension", "scientist"] },
    novelty: { number: "05A", title: "Audit novelty", subtitle: "Closest prior art, not just keywords", body: "Each candidate is compared with the closest known work. The comparison separates what already exists from the specific mechanism, empirical result, or task setting that would be new. A literature search cannot prove that no prior art exists.", inputs: "Candidate hypothesis and related source papers", outputs: "Explicit overlap · proposed difference · remaining novelty gaps", failure: "A renamed component or a combination already studied elsewhere should be rejected, revised, or searched further.", roles: ["novel", "audit", "prior"] },
    review: { number: "05B", title: "Adversarial review", subtitle: "Importance, controls, falsifiability", body: "Review asks whether the proposed contribution matters, whether the evidence supports it, and which result would falsify it. This is a critique of an idea—not an acceptance prediction or a paper-quality score.", inputs: "Hypothesis · evidence gaps · closest prior art", outputs: "Reviewer assessment · missing controls · rejection reasons", failure: "A plausible idea may still be trivial, confounded, computationally infeasible, or impossible to test with available data.", roles: ["review", "critic"] },
    experiment: { number: "06", title: "Design a decisive test", subtitle: "Plan → permission, never silent execution", body: "The experiment plan states datasets, splits, baselines, metrics, configuration, estimated compute, success conditions, and falsification conditions. Approval of a plan and authorization of compute are separate judgments. This application does not execute GPU jobs.", inputs: "Audited hypothesis and reviewer objections", outputs: "A minimal experiment specification · explicit permission record", failure: "No experiment result exists until actual execution evidence is recorded. Authorization alone never establishes performance.", roles: ["experiment", "plan"] },
    feedback: { number: "↺", title: "Researcher feedback loop", subtitle: "Challenge, revise, reject, investigate", body: "A researcher can challenge the evidence, revise a hypothesis, or record a decision and its reason. A challenge or directed investigation queues a real retrieval task. The next pass must be inspected; it is not guaranteed to rescue the candidate.", inputs: "Comments · counterexamples · missing controls · decision reasons", outputs: "Persistent decision history and targeted follow-up searches", failure: "Keep rejected and deferred candidates visible. Reopening a candidate does not erase the reasons it previously failed.", roles: ["investigate", "challenge"] }
  };

  function methodology() {
    const m = methods[ui.method];
    const node = key => `<button class="method-node" data-method="${key}" aria-pressed="${key === ui.method}"><span>${methods[key].number}</span><div><strong>${methods[key].title}</strong><small>${methods[key].subtitle}</small></div></button>`;
    const roleMap = { evidence: ["cartographer"], synthesis: ["tensions", "generator"], review: ["reviewer"] };
    const related = state.jobs.filter(j => [...m.roles, ...(roleMap[ui.method] || [])].some(role => `${j.kind} ${j.role}`.toLowerCase().includes(role)));
    return heading("PROCESS / EVIDENCE / HUMAN CONTROL", "Research methodology", "An inspectable research loop. Select a step to understand its evidence contract and failure modes.") +
      '<div class="notice"><strong>Independent assessments, SERIAL built-in worker execution.</strong> The branches separate novelty and reviewer judgments; they do not represent concurrent tasks. Parallel external investigators were used in the pilot only.</div>' +
      `<div class="method-layout"><section class="panel"><div class="panel-head"><h2>From question to a discriminating experiment</h2><span class="badge">Process map</span></div><div class="method-flow">${node("scope")}<div class="flow-arrow" aria-hidden="true">↓</div>${node("retrieve")}<div class="flow-arrow" aria-hidden="true">↓</div>${node("evidence")}<div class="flow-arrow" aria-hidden="true">↓</div>${node("synthesis")}<p class="branch-label">Independent assessments · serial worker</p><div class="flow-arrow" aria-hidden="true">↙ &nbsp;&nbsp;&nbsp; ↘</div><div class="method-branch">${node("novelty")}${node("review")}</div><div class="flow-arrow" aria-hidden="true">↘ &nbsp;&nbsp;&nbsp; ↙</div>${node("experiment")}<button class="method-feedback" data-method="feedback" aria-pressed="${ui.method === "feedback"}">↺ &nbsp; Researcher feedback → targeted retrieval → evidence store</button></div></section><aside class="stack">${panel(m.title, `<span class="eyebrow">STEP ${m.number} / ${esc(m.subtitle)}</span><p class="muted space-top">${esc(m.body)}</p>${section("Inputs", m.inputs)}${section("Outputs", m.outputs)}${section("Where this can fail", m.failure)}<div class="actions">${button("Inspect actual tasks", "go-observatory", "", "small cyan")}${button("Open evidence store", "go-library", "", "small")}</div>`)}${panel("Recorded work for this step", related.length ? related.map(j => `<div class="decision"><div class="row-top"><button class="text-button" data-action="open-job" data-id="${esc(j.id)}">${esc(j.role || j.kind)}</button>${badge(j.status)}</div><p>${esc(short(j.input?.query || j.kind))}</p></div>`).join("") : '<p class="hint">No matching tasks recorded in the selected campaign. The process map is explanatory, not a live execution graph.</p>')}${state.methodology.length ? panel("Persisted methodology records", state.methodology.map((record, i) => raw(record, text(record.title || record.name, `Methodology record ${i + 1}`))).join("")) : ""}</aside></div>${foundations()}`;
  }

  function foundations() {
    const records = state.foundations;
    const f = selected("foundations", ui.foundation) || records[0];
    return `<section class="panel foundations"><div class="panel-head"><div><span class="eyebrow">SOURCE-GROUNDED DESIGN FOUNDATIONS</span><h2>Scientific ideation, facet novelty & multi-agent research</h2></div><span class="badge">${records.length} source records</span></div>${f ? `<div class="foundation-layout"><div class="foundation-picker" role="group" aria-label="Research foundations">${records.map(record => `<button class="foundation-item" data-foundation="${esc(record.id)}" aria-pressed="${record.id === f.id}"><span class="mono dim">${esc(record.id)} · ${esc(record.date || "Date not recorded")}</span><strong>${esc(record.title || record.name || "Untitled foundation")}</strong></button>`).join("")}</div><div class="panel-body" id="foundation-inspector"><span class="eyebrow">FOUNDATION / ${esc(f.id)}</span><h2 class="inspector-title">${esc(f.title || f.name)}</h2><p class="hint">${esc(list(f.authors).map(a => typeof a === "object" ? a.name : a).join(", ") || "Authors not recorded")}</p><div class="source-actions">${link(f.url || f.source_url, "Read foundation source")}</div>${section("Supported insights", f.validated_insights || f.insights)}${section("Adaptation in this workbench", f.adaptation)}${section("Limits of this foundation", f.limits || f.limitations)}${section("What was actually examined", f.verification)}<section class="section"><h3>Source evidence</h3>${evidenceCards(f.evidence)}</section>${raw(f, "Inspect complete foundation record")}</div></div>` : empty("No foundation records in this campaign", "This view only exposes persisted sources. It does not import foundations from a different campaign or imply that a cited system validates this one.")}</section>`;
  }

  function openModal(title, description, body, formId, submit = "Save", attrs = "") {
    const modal = $("#modal");
    modal.innerHTML = `<form id="${formId}" ${attrs}><div class="modal-heading"><div><span class="eyebrow">RESEARCH RADAR</span><h2 id="modal-title">${esc(title)}</h2><p>${esc(description)}</p></div>${button("✕", "close-modal", 'type="button" aria-label="Close dialog"', "small subtle")}</div>${body}<p class="form-error" role="alert"></p><div class="form-footer">${button("Cancel", "close-modal", 'type="button"', "subtle")}<button class="button primary">${esc(submit)}</button></div></form>`;
    modal.showModal();
  }

  function campaignModal(configure = false) {
    const c = configure ? campaign() : null;
    const config = c?.config || {};
    const field = (label, name, value, extra = "") => `<label>${label}<input name="${name}" value="${esc(value)}" ${extra}></label>`;
    openModal(configure ? "Configure campaign" : "New research campaign", "Bound the inquiry before starting work. All budgets are explicit; no compute is executed automatically.",
      `<div class="form-grid">${field("Campaign name", "name", c?.name || "", "required maxlength=180")}${field("Research field", "field", c?.field || "", 'required placeholder="e.g. visual localization"')}<label class="full">Scientific question<textarea name="question" required placeholder="What unresolved mechanism or limitation should this campaign investigate?">${esc(config.question || "")}</textarea></label><label class="full">Retrieval queries · one per line<textarea name="queries" required placeholder="Specific paper, mechanism, or benchmark queries">${esc(list(config.queries).join("\n"))}</textarea></label>${field("Maximum papers", "max_papers", config.max_papers ?? 20, 'type="number" min="1" max="500" required')}${field("Maximum HTTP requests", "max_requests", config.max_requests ?? 40, 'type="number" min="1" max="1000" required')}${field("Time budget · seconds", "time_budget_seconds", config.time_budget_seconds ?? 600, 'type="number" min="1" max="86400" required')}${field("API budget · USD", "api_budget_usd", config.api_budget_usd ?? 0, 'type="number" min="0" step="0.01" required')}${field("Compute budget · GPU hours", "compute_budget_hours", config.compute_budget_hours ?? 0, 'type="number" min="0" step="0.1" required')}${field("Venues · comma separated", "venues", list(config.venues).join(", "))}${field("Published from", "date_from", config.date_from || "", 'type="date"')}${field("Published through", "date_to", config.date_to || "", 'type="date"')}<label class="full">Scope constraints<textarea name="constraints" placeholder="Include / exclude tasks, datasets, or evidence types…">${esc(typeof config.constraints === "string" ? config.constraints : config.constraints ? JSON.stringify(config.constraints) : "")}</textarea></label><label class="full">Additional configuration · JSON object<textarea name="extra_config" class="mono" placeholder='{"seed_papers": []}'>${esc(JSON.stringify(Object.fromEntries(Object.entries(config).filter(([key]) => !["question", "queries", "max_papers", "max_requests", "time_budget_seconds", "api_budget_usd", "compute_budget_hours", "venues", "date_from", "date_to", "constraints"].includes(key))), null, 2))}</textarea></label></div>`,
      "campaign-form", configure ? "Save configuration" : "Create campaign", `data-mode="${configure ? "configure" : "create"}"`);
    const form = $("#campaign-form");
    for (const [key, min, max] of [["max_papers", 1, 25], ["max_requests", 1, 100], ["time_budget_seconds", 10, 3600], ["api_budget_usd", 0, 0], ["compute_budget_hours", 0, 72]]) {
      form.elements[key].min = min;
      form.elements[key].max = max;
    }
    form.elements.api_budget_usd.readOnly = true;
    form.elements.api_budget_usd.title = "Paid external APIs are not supported; budget is zero.";
  }

  async function mutate(path, body, message, form) {
    if (ui.mutation) return false;
    ui.mutation = true;
    const submits = form ? [...form.querySelectorAll('button:not([type="button"])')] : [];
    submits.forEach(el => { el.disabled = true; });
    try {
      const result = await request(path, body);
      if (form?.id === "campaign-form" && form.dataset.mode === "create") {
        const id = result.campaign?.id || (typeof result.campaign === "string" ? result.campaign : null) || result.id;
        if (id) { ui.campaign = id; updateURL(); }
      }
      if ($("#modal").open && form && $("#modal").contains(form)) $("#modal").close();
      if (form?.id === "decision-form") { form.elements.reason.value = ""; }
      if (form?.id === "investigate-form") form.reset();
      toast(message);
      await refresh(true);
      return true;
    } catch (error) {
      const errorNode = form?.querySelector(".form-error");
      if (errorNode) errorNode.textContent = error.message;
      else showError(error.message);
      return false;
    } finally { ui.mutation = false; submits.forEach(el => { el.disabled = false; }); }
  }

  function updateURL() {
    const url = new URL(location.href);
    if (ui.campaign) url.searchParams.set("campaign", ui.campaign); else url.searchParams.delete("campaign");
    url.hash = ui.view;
    history.replaceState(null, "", url);
  }

  function navigate(view) {
    if (!Object.hasOwn(views, view)) return;
    ui.view = view;
    updateURL();
    render();
    $("#workspace").scrollTop = 0;
    if (matchMedia("(max-width: 800px)").matches) window.scrollTo(0, 0);
    $("#workspace").focus({ preventScroll: true });
  }

  document.addEventListener("click", async event => {
    const target = event.target.closest("button,[data-view]");
    if (!target || target.disabled) return;
    if (target.dataset.view) { ui.opportunity = ""; ui.comparing = false; navigate(target.dataset.view); return; }
    if (target.dataset.candidateTab) { ui.candidateTab = target.dataset.candidateTab; render(); $(`#tab-${ui.candidateTab.replace(" ", "-")}`)?.focus(); return; }
    if (target.dataset.method) { ui.method = target.dataset.method; render(); $(`[data-method="${ui.method}"]`)?.focus(); return; }
    if (target.dataset.foundation) { ui.foundation = target.dataset.foundation; render(); [...document.querySelectorAll("[data-foundation]")].find(el => el.dataset.foundation === ui.foundation)?.focus({ preventScroll: true }); return; }
    const action = target.dataset.action, id = target.dataset.id;
    if (!action) return;
    if (target.closest("form")) event.preventDefault();
    if (action === "refresh") await refresh(true);
    else if (action === "new-campaign") campaignModal();
    else if (action === "configure") campaignModal(true);
    else if (action === "close-modal") $("#modal").close();
    else if (action.startsWith("campaign-")) {
      const c = campaign(); if (!c) return;
      if (action === "campaign-cancel") openModal("Cancel campaign?", "Cancellation stops further campaign work. Existing evidence and decisions remain available.", '<p class="muted">Queued or running tasks may stop at their next safe interruption point.</p>', "cancel-form", "Cancel campaign");
      else await mutate(`/api/campaigns/${encodeURIComponent(c.id)}/${action.slice(9)}`, {}, `Campaign ${action.slice(9)} requested.`);
    }
    else if (["job-retry", "job-pause", "job-resume"].includes(action)) await mutate(`/api/jobs/${encodeURIComponent(id)}/${action.slice(4)}`, {}, `Task ${action.slice(4)} requested.`);
    else if (action === "job-redirect") openModal("Redirect research task", "Supply the specific source, mechanism, or control this task should investigate.", '<label class="field">New retrieval query<textarea name="query" required></textarea></label>', "redirect-form", "Redirect task", `data-id="${esc(id)}"`);
    else if (action === "inspect-job") { ui.job = id; render(); }
    else if (action === "close-job") { ui.job = ""; render(); }
    else if (action === "open-job") { ui.job = id; navigate("observatory"); }
    else if (action === "inspect-paper" || action === "landscape-paper") { ui.paper = id; render(); $("#paper-inspector").scrollIntoView({ block: "nearest" }); }
    else if (action === "open-paper") { ui.paper = id; navigate("library"); }
    else if (action === "close-paper") { ui.paper = ""; render(); }
    else if (action === "inspect-tension") { ui.tension = id; render(); }
    else if (action === "open-tension") { ui.tension = id; navigate("tensions"); }
    else if (action === "close-tension") { ui.tension = ""; render(); }
    else if (action === "open-opportunity") { ui.opportunity = id; ui.candidateTab = "Evidence"; ui.comparing = false; navigate("board"); }
    else if (action === "back-board") { ui.opportunity = ""; ui.comparing = false; render(); }
    else if (action === "clear-compare") { ui.compare.clear(); render(); }
    else if (action === "compare") { ui.comparing = true; render(); }
    else if (action === "clear-filters") { ui.filters = {}; render(); }
    else if (action === "filter-family") { ui.filters.family = target.dataset.family; render(); $("#filter-family")?.focus({ preventScroll: true }); }
    else if (action === "inspect-validation") { ui.validation = id; render(); }
    else if (action === "go-observatory") navigate("observatory");
    else if (action === "go-library") navigate("library");
    else if (action === "investigate") {
      if (!campaign()) { toast("Create a campaign before investigating a direction."); return; }
      openModal("Investigate a direction", "This queues real retrieval. The work remains bounded by the campaign’s resource limits.", '<label class="field">Specific retrieval query<textarea name="query" required placeholder="Which missing baseline, prior-art overlap, or alternative explanation?"></textarea></label><label class="field">Research note<textarea name="note"></textarea></label>', "investigation-modal-form", "Queue investigation", `data-id="${esc(id || "")}"`);
    }
    else if (action === "authorize") openModal("Record experiment authorization", "Permission only. This application has no GPU runner and will not execute the experiment.", '<div class="notice warning">Confirm that the dataset, baseline, resource budget, and falsification conditions in the plan are acceptable. This records a research decision, not a performance result.</div><label class="field">Authorization reason and constraints<textarea name="reason" required></textarea></label>', "authorize-form", "Record permission only", `data-id="${esc(id)}"`);
    else if (action === "record-result") openModal("Record an external experiment result", "Only record measurements from an experiment that actually ran elsewhere. This does not execute a command or GPU job.",
      '<div class="notice warning">The artifact and observations are researcher-supplied and independently unverified. Saving queues a reviewer follow-up; it does not certify the result.</div><label class="field">Artifact path or source URL<input name="artifact" required placeholder="Location of the actual run output"></label><label class="field">Measured observations<textarea name="observations" required placeholder="Actual measurements, protocol, and comparison conditions"></textarea></label><label class="field">Interpretation and limitations<textarea name="reason" required placeholder="How do these observations support or falsify the hypothesis?"></textarea></label>',
      "result-form", "Save external measurements", `data-id="${esc(id)}"`);
  });

  document.addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.target;
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const data = Object.fromEntries(new FormData(form));
    const c = campaign();
    if (form.id === "campaign-form") {
      let extra;
      try { extra = JSON.parse(data.extra_config || "{}"); if (!extra || typeof extra !== "object" || Array.isArray(extra)) throw new Error(); } catch { $(".form-error", form).textContent = "Additional configuration must be a valid JSON object."; return; }
      if (data.date_from && data.date_to && data.date_from > data.date_to) { $(".form-error", form).textContent = "The publication start date must not follow the end date."; return; }
      const config = { ...extra, question: data.question.trim(), queries: data.queries.split("\n").map(q => q.trim()).filter(Boolean), venues: data.venues.split(",").map(v => v.trim()).filter(Boolean), constraints: data.constraints.trim(), date_from: data.date_from, date_to: data.date_to };
      for (const key of ["max_papers", "max_requests", "time_budget_seconds", "api_budget_usd", "compute_budget_hours"]) config[key] = Number(data[key]);
      if (!config.queries.length || !config.question || !data.name.trim() || !data.field.trim()) { $(".form-error", form).textContent = "A name, field, question, and at least one retrieval query are required."; return; }
      await mutate(form.dataset.mode === "configure" ? `/api/campaigns/${encodeURIComponent(c.id)}/configure` : "/api/campaigns", { name: data.name.trim(), field: data.field.trim(), config }, "Campaign saved.", form);
    } else if (form.id === "cancel-form") await mutate(`/api/campaigns/${encodeURIComponent(c.id)}/cancel`, {}, "Campaign cancellation requested.", form);
    else if (form.id === "redirect-form") await mutate(`/api/jobs/${encodeURIComponent(form.dataset.id)}/redirect`, { query: data.query.trim() }, "Task redirected.", form);
    else if (["investigate-form", "investigation-modal-form"].includes(form.id)) {
      if (!c) { showError("Select a campaign first."); return; }
      await mutate(`/api/campaigns/${encodeURIComponent(c.id)}/investigate`, { query: data.query.trim(), ...(data.note ? { note: data.note } : {}), ...(form.dataset.id ? { opportunity_id: form.dataset.id } : {}) }, "Investigation queued. Inspect the observatory for real task progress.", form);
    } else if (form.id === "decision-form") {
      const body = { action: data.action, reason: data.reason.trim(), campaign_id: c?.id };
      if (!body.reason) { $(".form-error", form).textContent = "Record a specific reason for this judgment."; return; }
      if (["reject", "defer"].includes(data.action)) {
        if (!Object.hasOwn(reasonDimensions, data.dimension)) { $(".form-error", form).textContent = "Choose a reason dimension for this judgment."; return; }
        body.dimension = data.dimension;
      }
      if (data.action === "revise") { body.hypothesis = data.hypothesis.trim(); if (!body.hypothesis) { $(".form-error", form).textContent = "A revised hypothesis is required."; return; } }
      if (data.action === "prioritize") body.priority = Number(data.priority);
      await mutate(`/api/opportunities/${encodeURIComponent(form.dataset.id)}/decision`, body, data.action === "authorize" ? "Permission recorded. No experiment was executed." : "Research judgment saved.", form);
    } else if (form.id === "authorize-form") await mutate(`/api/opportunities/${encodeURIComponent(form.dataset.id)}/decision`, { action: "authorize", reason: data.reason.trim(), campaign_id: c?.id }, "Permission recorded. No experiment was executed.", form);
    else if (form.id === "result-form") {
      if (![data.artifact, data.observations, data.reason].every(value => value.trim())) { $(".form-error", form).textContent = "An actual artifact, observed measurements, and interpretation are required."; return; }
      await mutate(`/api/opportunities/${encodeURIComponent(form.dataset.id)}/decision`, { action: "result", campaign_id: c?.id, reason: data.reason.trim(), results: { artifact: data.artifact.trim(), observations: data.observations.trim() } }, "External measurements recorded as unverified. Reviewer follow-up queued; no experiment was executed.", form);
    }
  });

  document.addEventListener("change", async event => {
    const target = event.target;
    if (target.id === "campaign-select") {
      ui.campaign = target.value;
      ui.paper = ui.tension = ui.job = ui.opportunity = ui.validation = ui.foundation = "";
      ui.compare.clear(); ui.comparing = false; ui.filters = {}; ui.lastSnapshot = "";
      updateURL();
      $("#workspace").setAttribute("aria-busy", "true");
      if (ui.refreshing) {
        const wait = setInterval(() => { if (!ui.refreshing) { clearInterval(wait); void refresh(true); } }, 50);
      } else await refresh(true);
    } else if (target.dataset.libraryFilter) { ui.filters[target.dataset.libraryFilter] = target.value; render(); }
    else if (target.id === "board-sort") { ui.sort = target.value; render(); }
    else if (target.id === "board-status") { ui.boardStatus = target.value; render(); }
    else if (target.id === "board-dimension") { ui.boardDimension = target.value; render(); }
    else if (target.dataset.compare) {
      if (target.checked && ui.compare.size >= 3) { target.checked = false; toast("Compare at most three candidates. Remove one selection first."); return; }
      if (target.checked) ui.compare.add(target.dataset.compare); else ui.compare.delete(target.dataset.compare);
      render();
    } else if (target.id === "decision-action") {
      updateDecisionFields();
    }
  });

  document.addEventListener("input", event => {
    const target = event.target;
    if (target.type !== "search") return;
    const position = target.selectionStart;
    if (target.dataset.libraryFilter) ui.filters[target.dataset.libraryFilter] = target.value;
    else if (target.dataset.filter === "board") ui.boardQuery = target.value;
    else if (target.dataset.filter === "trace") ui.traceQuery = target.value;
    else return;
    const id = target.id;
    render();
    const replacement = document.getElementById(id);
    replacement?.focus({ preventScroll: true });
    if (position != null) replacement?.setSelectionRange(position, position);
  });

  document.addEventListener("keydown", event => {
    if (event.target.closest("[role=tablist]") && ["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const tabs = [...document.querySelectorAll("[data-candidate-tab]")];
      const current = tabs.indexOf(event.target);
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      tabs[next].click();
      return;
    }
    if (event.key === "Escape" && !$("#modal").open && !editing()) {
      ui.paper = ui.tension = ui.job = ui.opportunity = "";
      ui.comparing = false; render(); $("#workspace").focus();
    }
    if (event.key === "/" && !editing() && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      if (!["library", "board", "observatory"].includes(ui.view)) navigate("library");
      $("#workspace input[type=search]")?.focus();
    }
  });
  $("#modal").addEventListener("close", () => { if (ui.dirty && !ui.mutation) render(); });
  window.addEventListener("hashchange", () => { if (Object.hasOwn(views, location.hash.slice(1))) navigate(location.hash.slice(1)); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) void refresh(); });
  setInterval(() => { if (!document.hidden && !ui.mutation) { if (ui.dirty && !editing()) render(); void refresh(); } }, 2000);
  void refresh(true);
})();
