/**
 * LEXIA content script — shows a slide-in notification the first time
 * a user visits a supported site each day.
 */

const SUPPORTED = new Set([
  "openai.com","chatgpt.com","chat.openai.com",
  "twitter.com","x.com",
  "klarna.com",
  "anthropic.com","claude.ai","claude.com",
  "facebook.com","instagram.com","messenger.com",
]);

function currentDomain() {
  return location.hostname.replace(/^www\./, "");
}

function todayKey(domain) {
  return `lexia:shown:${domain}:${new Date().toISOString().slice(0,10)}`;
}

function alreadyShownToday(domain) {
  try {
    return !!sessionStorage.getItem(todayKey(domain));
  } catch { return false; }
}

function markShown(domain) {
  try { sessionStorage.setItem(todayKey(domain), "1"); } catch {}
}

/* ── Banner HTML + CSS injected into the host page ─────────────────────── */
const SEM_CONFIG = {
  red:    { emoji: "🔴", bg: "#C0392B", msg: "Significant concerns found" },
  orange: { emoji: "🟠", bg: "#E67E22", msg: "Partial compliance detected" },
  green:  { emoji: "🟢", bg: "#27AE60", msg: "Good compliance detected" },
};

function injectBanner(data) {
  if (document.getElementById("lexia-banner")) return;

  const site = data.site || {};
  const sem  = site.semaphore || "orange";
  const cfg  = SEM_CONFIG[sem] || SEM_CONFIG.orange;
  const name = site.name || currentDomain();

  const style = document.createElement("style");
  style.textContent = `
    #lexia-banner {
      all: initial;
      position: fixed; bottom: 24px; right: 24px; z-index: 2147483647;
      font-family: system-ui, -apple-system, sans-serif;
      width: 300px;
      background: #1A1D2E;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,.45);
      overflow: hidden;
      transform: translateY(120%);
      transition: transform 350ms cubic-bezier(.34,1.56,.64,1);
      cursor: default;
    }
    #lexia-banner.lexia-in { transform: translateY(0); }
    #lexia-banner * { all: unset; box-sizing: border-box; }
    #lexia-bar {
      display: block; width: 100%; height: 5px;
      background: ${cfg.bg};
    }
    #lexia-body {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 14px;
    }
    #lexia-face { font-size: 28px; flex-shrink: 0; line-height: 1; }
    #lexia-text { flex: 1; min-width: 0; }
    #lexia-title {
      display: block;
      font-size: 13px; font-weight: 800; color: #fff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    #lexia-sub { display: block; font-size: 11px; color: #9aa0bd; margin-top: 2px; }
    #lexia-close {
      color: #6b7280; font-size: 18px; cursor: pointer; line-height: 1;
      padding: 4px; flex-shrink: 0;
    }
    #lexia-close:hover { color: #fff; }
    #lexia-foot {
      display: flex; gap: 8px;
      padding: 0 14px 14px;
    }
    #lexia-cta {
      display: block; flex: 1; text-align: center;
      background: #003399; color: #fff;
      font-size: 12px; font-weight: 700;
      padding: 8px 12px; border-radius: 10px;
      cursor: pointer;
    }
    #lexia-cta:hover { background: #002a7a; }
    #lexia-wordmark {
      display: block;
      font-size: 10px; font-weight: 800; letter-spacing: .12em;
      color: #FFCC00; padding: 8px 14px 0;
    }
  `;
  document.head.appendChild(style);

  const banner = document.createElement("div");
  banner.id = "lexia-banner";
  banner.setAttribute("role", "alertdialog");
  banner.setAttribute("aria-label", `LEXIA compliance alert for ${name}`);
  banner.innerHTML = `
    <span id="lexia-bar"></span>
    <span id="lexia-wordmark">LEXIA</span>
    <div id="lexia-body">
      <span id="lexia-face" aria-hidden="true">${cfg.emoji}</span>
      <span id="lexia-text">
        <span id="lexia-title">${name}</span>
        <span id="lexia-sub">${cfg.msg} · Score ${site.semaphore_score ?? "?"}/100</span>
      </span>
      <span id="lexia-close" role="button" tabindex="0" aria-label="Dismiss">✕</span>
    </div>
    <div id="lexia-foot">
      <span id="lexia-cta" role="button" tabindex="0">See your rights →</span>
    </div>
  `;
  document.body.appendChild(banner);

  // Slide in after a short delay
  requestAnimationFrame(() => requestAnimationFrame(() => banner.classList.add("lexia-in")));

  // Auto-dismiss after 9 seconds
  const autoDismiss = setTimeout(() => closeBanner(), 9000);

  function closeBanner() {
    clearTimeout(autoDismiss);
    banner.classList.remove("lexia-in");
    setTimeout(() => banner.remove(), 400);
  }

  banner.querySelector("#lexia-close").addEventListener("click", closeBanner);
  banner.querySelector("#lexia-close").addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") closeBanner();
  });

  banner.querySelector("#lexia-cta").addEventListener("click", () => {
    closeBanner();
    chrome.runtime.sendMessage({ type: "OPEN_POPUP" });
  });
  banner.querySelector("#lexia-cta").addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") {
      closeBanner();
      chrome.runtime.sendMessage({ type: "OPEN_POPUP" });
    }
  });
}

/* ── Bootstrap ──────────────────────────────────────────────────────────── */
const domain = currentDomain();
if (SUPPORTED.has(domain) && !alreadyShownToday(domain)) {
  markShown(domain);
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "LEXIA_DATA" && msg.data && !msg.data.error) {
      injectBanner(msg.data);
    }
  });
  chrome.runtime.sendMessage({ type: "PAGE_LOADED", href: location.href });
}
