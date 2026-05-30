/**
 * LEXIA Popup JS — reads data from chrome.storage.local and renders the UI.
 */

/* ── Icon library ─────────────────────────────────────────────────────────── */
// Real PNG icons mapped by concept ID (from extension/icons/)
const ICON_BY_ID = {
  right_explanation:     "icons/right__right_explanation.png",
  right_human_oversight: "icons/right__right_human_oversight.png",
  right_ai_transparency: "icons/right__right_chatbot_disclosure.png",
  right_complaint:       "icons/right__right_complaint.png",
  right_erasure:         "icons/right__right_erasure.png",
  right_contest:         "icons/right__right_contest.png",
  no_ai_disclosure:      "icons/risk__no_ai_disclosure.png",
  training_on_user_data: "icons/risk__training_on_user_data.png",
  profiling:             "icons/risk__profiling.png",
  third_party_sharing:   "icons/risk__third_party_sharing.png",
};

const I = (paths) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;

const FALLBACK_SVG = I('<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9h6v6H9z"/>');

function conceptIcon(conceptKey, itemId) {
  const src = ICON_BY_ID[itemId] || ICON_BY_ID[conceptKey];
  if (src) {
    return `<img src="${src}" alt="" aria-hidden="true">`;
  }
  return FALLBACK_SVG;
}

/* ── Badge metadata ───────────────────────────────────────────────────────── */
const STATUS_META = {
  granted:  { adult: "Protected",   child: "✅ Safe!",            icon: '<path d="M5 12l4 4L19 7"/>',                                                                                               emoji: "✅", glyph: "✓" },
  violated: { adult: "At risk",     child: "❌ Not OK!",          icon: '<path d="M12 8v5"/><path d="M12 16.5h.01"/><path d="M10.3 4.3 2.7 18a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z"/>', emoji: "❌", glyph: "✗" },
  unknown:  { adult: "Unknown",     child: "🤷 Don't know yet",   icon: '<circle cx="12" cy="12" r="9"/><path d="M9.8 9.5a2.2 2.2 0 0 1 4.3.7c0 1.5-2.2 2.2-2.2 2.2"/><path d="M12 16.2h.01"/>', emoji: "🤷", glyph: "?" },
};
const SEVERITY_META = {
  critical: { adult: "Critical", child: "🛑 Super serious!",  icon: '<path d="M10.3 4.3 2.7 18a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 16.5h.01"/>', emoji: "🛑", glyph: "!!" },
  high:     { adult: "High",     child: "⚠️ Pretty serious",  icon: '<path d="M10.3 4.3 2.7 18a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 16.5h.01"/>', emoji: "⚠️", glyph: "!" },
  medium:   { adult: "Medium",   child: "👀 Watch out",       icon: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 15.5h.01"/>',                                                               emoji: "👀", glyph: "~" },
  low:      { adult: "Low",      child: "💙 Small thing",     icon: '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01"/><path d="M11 12h1v4h1"/>',                                                 emoji: "💙", glyph: "·" },
};
const SEM_META = {
  red:    { label: "High concern",       child: "Uh oh! 😟 This app has big problems",   color: "var(--color-red)",    },
  orange: { label: "Partial compliance", child: "Getting better… 🤔 Some things to fix!", color: "var(--color-orange)", },
  green:  { label: "Compliant",          child: "Yay! 🎉 This app is being good!",        color: "var(--color-green)",  },
};

/* ── Semaphore SVGs ───────────────────────────────────────────────────────── */
function lampSVG(kind) {
  if (kind === "red")
    return '<svg viewBox="0 0 30 30" aria-hidden="true"><rect x="5" y="5" width="20" height="20" rx="3" fill="#C0392B" stroke="#C0392B" stroke-width="2"/></svg>';
  if (kind === "orange")
    return '<svg viewBox="0 0 30 30" aria-hidden="true">'
      + '<defs><clipPath id="diaHalf"><rect x="0" y="0" width="15" height="30"/></clipPath></defs>'
      + '<path d="M15 3 L27 15 L15 27 L3 15 Z" fill="none" stroke="#E67E22" stroke-width="2.4" stroke-linejoin="round"/>'
      + '<path d="M15 3 L27 15 L15 27 L3 15 Z" fill="#E67E22" clip-path="url(#diaHalf)"/></svg>';
  return '<svg viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="10.5" fill="none" stroke="#27AE60" stroke-width="3"/></svg>';
}
function shapeMini(kind) {
  if (kind === "red")
    return '<svg class="shape" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="2" width="12" height="12" rx="2" fill="#C0392B"/></svg>';
  if (kind === "orange")
    return '<svg class="shape" viewBox="0 0 16 16" aria-hidden="true"><defs><clipPath id="dm"><rect x="0" y="0" width="8" height="16"/></clipPath></defs><path d="M8 1 14 8 8 15 2 8Z" fill="none" stroke="#E67E22" stroke-width="1.8" stroke-linejoin="round"/><path d="M8 1 14 8 8 15 2 8Z" fill="#E67E22" clip-path="url(#dm)"/></svg>';
  return '<svg class="shape" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5.5" fill="none" stroke="#27AE60" stroke-width="2.4"/></svg>';
}

/* ── State ────────────────────────────────────────────────────────────────── */
let APP = { data: null, mode: "adult", aknOpenerEl: null };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ── Semaphore renderer ───────────────────────────────────────────────────── */
const SEM_CHILD = {
  red:    { face: "😟", bg: "linear-gradient(135deg,#C0392B,#e74c3c)", msg: "Uh oh! This app needs to follow the rules better!", tip: "It has some big problems we found." },
  orange: { face: "🤔", bg: "linear-gradient(135deg,#E67E22,#f39c12)", msg: "Getting better… but some things could still improve!", tip: "There are a few things to fix." },
  green:  { face: "😊", bg: "linear-gradient(135deg,#27AE60,#2ecc71)", msg: "Yay! 🎉 This app is following the rules!", tip: "Great job! It looks pretty safe." },
};

function _stars(score) {
  const filled = Math.round((score / 100) * 5);
  return [1,2,3,4,5].map(i =>
    `<span style="font-size:22px;opacity:${i <= filled ? '1' : '0.25'}">${i <= filled ? "⭐" : "☆"}</span>`
  ).join("");
}

function renderSemaphore() {
  const s = APP.data.site;
  const meta = SEM_META[s.semaphore] || SEM_META.orange;
  const isChild = APP.mode === "child";

  if (isChild) {
    const c = SEM_CHILD[s.semaphore] || SEM_CHILD.orange;
    $("semaphore").style.cssText = `background:${c.bg};border-radius:22px;padding:18px;color:#fff;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center`;
    $("semaphore").innerHTML = `
      <div style="font-size:56px;line-height:1;filter:drop-shadow(0 4px 8px rgba(0,0,0,.25))" aria-hidden="true">${c.face}</div>
      <div style="font-size:15px;font-weight:800;line-height:1.3">${esc(c.msg)}</div>
      <div style="font-size:12px;opacity:.85">${esc(c.tip)}</div>
      <div id="scoreToggle" role="button" tabindex="0" aria-expanded="false" aria-controls="scorePanel"
           style="cursor:pointer;background:rgba(255,255,255,.18);border-radius:16px;padding:10px 18px;width:100%"
           title="Tap to see why!">
        <div style="display:flex;justify-content:center;gap:2px;margin-bottom:4px" aria-label="Score: ${s.semaphore_score} out of 100">${_stars(s.semaphore_score)}</div>
        <div style="font-size:11px;opacity:.8">👆 Tap to see why!</div>
      </div>`;
    $("semaphore").setAttribute("aria-label",
      `This app's score: ${_stars(s.semaphore_score).replace(/<[^>]+>/g,"")}. ${c.msg}`);
    return;
  }

  // Adult mode
  const semLabel = meta.label;
  const lights = ["red", "orange", "green"]
    .map((k) => `<span class="lamp ${k} ${k === s.semaphore ? "on" : ""}">${lampSVG(k)}</span>`)
    .join("");
  $("semaphore").style.cssText = "";
  $("semaphore").innerHTML = `
    <div class="lights" aria-hidden="true">${lights}</div>
    <div class="sem-info">
      <span class="sem-state" style="color:${meta.color}">${shapeMini(s.semaphore)}${esc(semLabel)}</span>
      <div class="sem-label">${esc(s.semaphore_label || "")}</div>
      <div class="score-wrap" id="scoreToggle" role="button" tabindex="0" aria-expanded="false" aria-controls="scorePanel" title="Click to see how the score is calculated">
        <div class="score-row"><span class="k">Compliance score</span><span class="v">${s.semaphore_score}/100</span></div>
        <div class="bar" role="progressbar" aria-valuenow="${s.semaphore_score}" aria-valuemin="0" aria-valuemax="100" aria-label="Compliance score ${s.semaphore_score} out of 100">
          <i style="width:${s.semaphore_score}%;background:${meta.color}"></i>
        </div>
        <div class="score-hint">▼ tap to see breakdown</div>
      </div>
    </div>`;
  $("semaphore").setAttribute("aria-label",
    `Compliance status: ${semLabel}. ${s.semaphore_label || ""}. Score ${s.semaphore_score} out of 100.`);
}

/* ── Badge HTML ───────────────────────────────────────────────────────────── */
function badgeHTML(kind, meta, isChild) {
  const text = isChild ? meta.child : meta.adult;
  if (isChild)
    return `<span class="badge ${kind}"><span aria-hidden="true">${meta.emoji}</span>${esc(text)}</span>`;
  return `<span class="badge ${kind}">${I(meta.icon)}<span class="sr-only">${esc(text)}: </span>${esc(text)}</span>`;
}

/* ── Card HTML ────────────────────────────────────────────────────────────── */
function cardHTML(item, kind, badgeKind, badgeMeta) {
  const isChild = APP.mode === "child";
  const ovr = isChild ? (CHILD_OVERRIDES[item.id] || {}) : {};
  const title = ovr.label || (isChild ? item.label_child : item.label);
  const desc  = ovr.desc  || (isChild ? item.description_child : item.description);
  const evidence = item.evidence;
  const regionLabel = `${title} — ${isChild ? badgeMeta.child : badgeMeta.adult}`;
  const articleLabel = item.akn_ref ? item.akn_ref.article : "";

  const evidenceBlock = (evidence && kind === "right")
    ? `<div class="evidence-block" aria-label="Evidence from ToS">"${esc(evidence)}"</div>`
    : "";

  return `
  <div class="card" data-open="false" role="region" aria-label="${esc(regionLabel)}">
    <button class="card-head" type="button" aria-expanded="false" data-card="${esc(item.id)}">
      <span class="card-ico" aria-hidden="true">${conceptIcon(item.concept, item.id)}</span>
      <span class="card-main">
        <span class="card-title">${esc(title)}</span>
        <span class="card-sub">${badgeHTML(badgeKind, badgeMeta, isChild)}</span>
      </span>
      <svg class="card-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
    </button>
    <div class="card-body"><div><div class="card-body-inner">
      <p class="card-desc">${esc(desc)}</p>
      ${evidenceBlock}
      ${item.akn_ref ? `<button class="src-btn" type="button" data-src="${esc(item.id)}" data-kind="${kind}">
        See legal source <span class="art" aria-hidden="true">${esc(articleLabel)} →</span>
      </button>` : ""}
    </div></div></div>
  </div>`;
}

/* ── Section renderers ────────────────────────────────────────────────────── */
function renderRights() {
  const isChild = APP.mode === "child";
  $("rightsHeading").textContent = isChild ? "✨ Things you can do!" : "Your Rights";
  $("rightsCount").textContent = APP.data.rights.length;
  $("rightsList").innerHTML = APP.data.rights
    .map((r) => cardHTML(r, "right", r.status, STATUS_META[r.status] || STATUS_META.unknown))
    .join("");
}
function renderRisks() {
  const isChild = APP.mode === "child";
  $("risksHeading").textContent = isChild ? "⚠️ Watch out for this!" : "Detected Risks";
  $("risksCount").textContent = APP.data.risks.length;
  $("risksList").innerHTML = APP.data.risks
    .map((r) => cardHTML(r, "risk", r.severity, SEVERITY_META[r.severity] || SEVERITY_META.medium))
    .join("");
}

/* ── Mode ─────────────────────────────────────────────────────────────────── */
function applyMode() {
  const isChild = APP.mode === "child";
  $("popup").dataset.mode = APP.mode;
  $("modeCaption").textContent = isChild ? "Child-friendly mode" : "Adult mode";
  const sw = $("modeSwitch");
  sw.setAttribute("aria-checked", String(isChild));
  sw.setAttribute("aria-label", isChild
    ? "Reading mode: Child-friendly. Switch to Adult mode."
    : "Reading mode: Adult. Switch to Child-friendly mode.");
  if (APP.data) {
    $("siteName").textContent = APP.data.site.name || APP.data.site.domain;
    $("favicon").textContent = (APP.data.site.favicon_letter || APP.data.site.name || "?")[0].toUpperCase();
  }
}

/* ── Main render ──────────────────────────────────────────────────────────── */
function renderPlugin(data) {
  APP.data = data;
  const saved = (() => { try { return localStorage.getItem("lexia.mode"); } catch { return null; } })();
  if (saved === "adult" || saved === "child") APP.mode = saved;
  else APP.mode = data.mode || "adult";

  $("loadingScreen").style.display = "none";
  $("errorScreen").style.display = "none";
  const mc = $("mainContent");
  mc.style.display = "flex";
  mc.style.flexDirection = "column";
  mc.style.gap = "14px";

  applyMode();
  renderSemaphore();
  renderScorePanel();
  renderRisks();
  renderRights();
  renderPolicyLink();
}

/* ── Score breakdown panel ────────────────────────────────────────────────── */
const STATUS_LABEL = { granted: "confirmed", violated: "denied", unknown: "unknown" };

const CHILD_STATUS_LABEL = { granted: "✅ Found!", violated: "❌ Blocked!", unknown: "🤷 Not found" };
const ADULT_STATUS_LABEL = { granted: "confirmed", violated: "denied", unknown: "unknown" };

function renderScorePanel() {
  const s = APP.data.site;
  const breakdown = s.score_breakdown || [];
  if (!breakdown.length) return;
  const isChild = APP.mode === "child";

  if ($("scorePanelTitle")) {
    $("scorePanelTitle").textContent = isChild ? "Why does this app get this score? 🤔" : "How is this score calculated?";
  }
  if (isChild) {
    $("scoreFormula").textContent = "We start with 100 points ✨ — then subtract points for each problem we find, and add points for each right the app gives you!";
  } else {
    $("scoreFormula").textContent = s.score_formula || "";
  }

  const statusLabels = isChild ? CHILD_STATUS_LABEL : ADULT_STATUS_LABEL;
  const rows = breakdown.map(row => {
    const deltaClass = row.delta < 0 ? "neg" : row.delta > 0 ? "pos" : "zero";
    const deltaText  = row.delta === 0 ? "👍 OK" : (row.delta > 0 ? `+${row.delta}` : `${row.delta}`);
    const icon = row.type === "risk" ? "⚠️" : "✨";
    const statusTxt = statusLabels[row.status] || row.status;
    return `<tr>
      <td class="td-label">${icon} ${esc(row.label)}</td>
      <td class="td-status">${esc(statusTxt)}</td>
      <td class="td-delta ${deltaClass}">${deltaText}${row.delta !== 0 ? (isChild ? "" : " pts") : ""}</td>
    </tr>`;
  }).join("");

  const thStyle = "text-align:left;font-size:10px;color:var(--color-text-muted);padding:0 2px 6px;font-weight:700";
  $("scoreTable").innerHTML = `<thead><tr>
    <th style="${thStyle}">${isChild ? "What we checked 🔍" : "Concept"}</th>
    <th style="${thStyle}">${isChild ? "What we found" : "Status"}</th>
    <th style="${thStyle};text-align:right">${isChild ? "Points 🎯" : "Points"}</th>
  </tr></thead><tbody>${rows}</tbody>`;

  // Wire toggle
  const toggle = $("scoreToggle");
  if (toggle && !toggle._wired) {
    toggle._wired = true;
    const panel = $("scorePanel");
    const handler = () => {
      const open = !panel.hidden;
      panel.hidden = open;
      toggle.setAttribute("aria-expanded", String(!open));
    };
    toggle.addEventListener("click", handler);
    toggle.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handler(); }});
  }
}

function renderPolicyLink() {
  const url = APP.data?.site?.policy_url;
  const ftr = document.querySelector(".ftr");
  if (!ftr) return;
  const existing = ftr.querySelector(".policy-link");
  if (existing) existing.remove();
  if (url) {
    const a = document.createElement("a");
    a.className = "policy-link";
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = "📄 Privacy Policy ↗";
    a.style.cssText = "display:block;margin-top:5px;color:#003399;font-size:11px;font-weight:600;text-decoration:none;";
    ftr.appendChild(a);
  }
}

function showError(title, sub) {
  $("loadingScreen").style.display = "none";
  $("errorTitle").textContent = title;
  $("errorSub").textContent = sub;
  $("errorScreen").style.display = "flex";
  $("siteName").textContent = "Unknown site";
  $("favicon").textContent = "?";
}

/* ── AKN panel ────────────────────────────────────────────────────────────── */
let lastFocusable = [];
function findRef(id) {
  if (!APP.data) return null;
  return [...(APP.data.rights || []), ...(APP.data.risks || [])].find((x) => x.id === id);
}
function _renderRef(ref) {
  const t = ref.text || "";
  const a = Math.max(0, ref.highlight_start || 0);
  const b = Math.min(t.length, ref.highlight_end || t.length);
  const highlighted = b > a
    ? esc(t.slice(0, a)) + "<mark>" + esc(t.slice(a, b)) + "</mark>" + esc(t.slice(b))
    : esc(t);
  return `<div class="akn-source-block">
    <div class="akn-source-reg">${esc(ref.regulation || "")}</div>
    <div class="akn-source-art">${esc(ref.article || "")}</div>
    <div class="akn-source-text">${highlighted}</div>
    <a class="akn-source-link" href="${esc(ref.official_url || "#")}" target="_blank" rel="noopener noreferrer">EUR-Lex ↗</a>
  </div>`;
}

function openAKN(id, opener) {
  const item = findRef(id);
  if (!item || !item.akn_ref) return;
  APP.aknOpenerEl = opener || document.activeElement;

  // Use all refs if available, otherwise fall back to primary
  const refs = (item.akn_refs && item.akn_refs.length) ? item.akn_refs : [item.akn_ref];
  const primary = refs[0];

  // Eyebrow: list all regulations
  const regs = [...new Set(refs.map(r => r.regulation).filter(Boolean))];
  $("aknRegulation").textContent = `Legal source · ${regs.join(" + ") || "EU AI Act"}`;
  $("aknArt").textContent = primary.article || "Article";

  // Body: render each reference block
  $("aknText").innerHTML = refs.map(_renderRef).join('<hr style="border:none;border-top:1px solid #DDE1EC;margin:8px 0">');

  // Footer link → primary source
  $("aknLink").href = primary.official_url || "#";

  const akn = $("akn");
  akn.hidden = false;
  requestAnimationFrame(() => {
    $("scrim").dataset.open = "true";
    akn.dataset.open = "true";
    $("aknClose").focus();
  });
  refreshFocusable();
  document.addEventListener("keydown", onAknKeydown, true);
}
function closeAKN() {
  const akn = $("akn");
  akn.dataset.open = "false";
  $("scrim").dataset.open = "false";
  document.removeEventListener("keydown", onAknKeydown, true);
  const back = APP.aknOpenerEl;
  setTimeout(() => { akn.hidden = true; if (back && back.focus) back.focus(); }, 200);
}
function refreshFocusable() {
  lastFocusable = [...$("akn").querySelectorAll('button, a[href], [tabindex]:not([tabindex="-1"])')]
    .filter((el) => !el.disabled && el.offsetParent !== null);
}
function onAknKeydown(e) {
  if (e.key === "Escape") { e.preventDefault(); closeAKN(); return; }
  if (e.key !== "Tab" || !lastFocusable.length) return;
  const first = lastFocusable[0], last = lastFocusable[lastFocusable.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

/* ── Section + card toggles ───────────────────────────────────────────────── */
function toggleSection(sectionEl) {
  const open = sectionEl.dataset.open === "true";
  sectionEl.dataset.open = String(!open);
  sectionEl.querySelector(".sec-head").setAttribute("aria-expanded", String(!open));
}
function toggleCard(headBtn) {
  const card = headBtn.closest(".card");
  const open = card.dataset.open === "true";
  card.dataset.open = String(!open);
  headBtn.setAttribute("aria-expanded", String(!open));
}

/* ── Event wiring ─────────────────────────────────────────────────────────── */
function wire() {
  $("modeSwitch").addEventListener("click", () => {
    APP.mode = APP.mode === "child" ? "adult" : "child";
    try { localStorage.setItem("lexia.mode", APP.mode); } catch {}
    applyMode();
    if (APP.data) {
      renderSemaphore();
      renderScorePanel();
      renderRisks();
      renderRights();
      renderPolicyLink();
    }
  });

  document.querySelectorAll(".sec-head").forEach((btn) => {
    btn.addEventListener("click", () => toggleSection(btn.closest(".section")));
  });

  $("main").addEventListener("click", (e) => {
    const src = e.target.closest(".src-btn");
    if (src) { e.stopPropagation(); openAKN(src.dataset.src, src); return; }
    const head = e.target.closest(".card-head");
    if (head) toggleCard(head);
  });

  $("aknClose").addEventListener("click", closeAKN);
  $("scrim").addEventListener("click", closeAKN);
}

/* ── Bootstrap ────────────────────────────────────────────────────────────── */
/* ── Child-friendly overrides (no legal jargon) ───────────────────────────── */
const CHILD_OVERRIDES = {
  right_explanation:     {
    label: "You can ask WHY! 🙋",
    desc:  "If this robot makes a big decision about you, you can ask a grown-up to explain why — in simple words you can understand!",
  },
  right_human_oversight: {
    label: "A grown-up watches the robot 👀",
    desc:  "There must always be a real person who can check what the robot does, and press the STOP button if something goes wrong!",
  },
  right_ai_transparency: {
    label: "The robot must say it's a robot 🤖",
    desc:  "Before you start chatting, the robot must say \"Hi! I am a computer, not a real person!\" That's the rule!",
  },
  right_complaint:       {
    label: "You can tell the government! 📢",
    desc:  "If a robot is being unfair to you, you can tell special government people who check these things — and they MUST listen!",
  },
  right_erasure:         {
    label: "Make them forget you 🗑️",
    desc:  "You can ask them to delete everything they know about you — like pressing DELETE on your own profile!",
  },
  right_contest:         {
    label: "You can say \"That's not fair!\" ✊",
    desc:  "If the robot decides something bad about you, a real person must be able to say: \"Wait, let me check that again!\"",
  },
  no_ai_disclosure:      {
    label: "They didn't say it's a robot! 😮",
    desc:  "This app uses a robot to talk to you, but it forgot to say so! That's against the rules — robots must always introduce themselves!",
  },
  training_on_user_data: {
    label: "The robot learns from YOU 📚",
    desc:  "What you type might be used to teach the robot new things. Always ask a parent if you're OK with that before you use it!",
  },
  profiling:             {
    label: "They build a profile about you 🕵️",
    desc:  "They watch everything you do and make a list: what you like, what you click, where you go. That's a bit sneaky, right?",
  },
  third_party_sharing:   {
    label: "They share your info with others 📤",
    desc:  "This company tells other companies about you — without asking you first! You should be able to say NO to that!",
  },
};

const DEMO_DOMAINS = ["openai.com", "twitter.com", "klarna.com", "anthropic.com", "facebook.com"];

async function getCurrentDomain() {
  return new Promise((resolve) => {
    if (typeof chrome === "undefined" || !chrome.tabs) {
      // Running as a plain webpage (test mode) — use URL param ?domain= or default
      const param = new URLSearchParams(window.location.search).get("domain");
      if (param && DEMO_DOMAINS.includes(param)) { resolve(param); return; }
      resolve("openai.com");
      return;
    }
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0] || !tabs[0].url) { resolve(""); return; }
      try {
        const u = new URL(tabs[0].url);
        resolve(u.hostname.replace(/^www\./, ""));
      } catch { resolve(""); }
    });
  });
}

async function _fetchFromAPI(domain) {
  const resp = await fetch(`http://localhost:5050/api/site/${domain}`, {
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    return { error: true, message: err.message || "Not in database" };
  }
  return resp.json();
}

async function _updateStorage(key, data) {
  if (typeof chrome !== "undefined" && chrome.storage) {
    await chrome.storage.local.set({ [key]: { ...data, _cachedAt: Date.now() } });
  }
}

async function loadData(domain) {
  if (!domain) { showError("No active tab", "Open a website to check compliance."); return; }

  $("siteName").textContent = domain;
  $("favicon").textContent = domain[0].toUpperCase();

  const key = `lexia:${domain}`;

  // Always fetch fresh from API — show cached data immediately while fetching
  const stored = await new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.local.get(key, (r) => resolve(r[key] || null));
    } else {
      resolve(null);
    }
  });

  if (stored && !stored.error) {
    renderPlugin(stored); // show cached immediately
  }

  // Always refetch fresh data from API
  try {
    const data = await _fetchFromAPI(domain);
    if (data.error) {
      if (!stored) showError("Site not in database",
        "Supported: openai.com · twitter.com · klarna.com · anthropic.com · facebook.com");
    } else {
      renderPlugin(data);              // re-render with fresh data
      await _updateStorage(key, data); // update cache
    }
  } catch {
    if (!stored) {
      const poll = async (attempts = 0) => {
        try {
          const data = await _fetchFromAPI(domain);
          if (!data.error) { renderPlugin(data); await _updateStorage(key, data); }
          else showError("Backend unavailable", "Start the API server: python backend/api/app.py");
        } catch {
          if (attempts < 2) setTimeout(() => poll(attempts + 1), 800);
          else showError("Backend unavailable", "Start the API server: python backend/api/app.py");
        }
      };
      poll();
    }
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  wire();
  const domain = await getCurrentDomain();
  loadData(domain);
});
