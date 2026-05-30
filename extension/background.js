/**
 * LEXIA service worker
 * - Fetches compliance data when the user navigates to a supported site
 * - Sets a colored badge on the extension icon
 * - Sends data to content.js to show a first-visit-per-day notification
 * - Handles OPEN_POPUP requests from content.js
 */

const API_BASE     = "http://localhost:5050";
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

const BADGE_COLOR = {
  red:    "#C0392B",
  orange: "#E67E22",
  green:  "#27AE60",
};

function extractDomain(url) {
  try {
    const u = new URL(url);
    if (!["http:","https:"].includes(u.protocol)) return null;
    return u.hostname.replace(/^www\./, "");
  } catch { return null; }
}

async function fetchAndStore(domain, tabId) {
  const key = `lexia:${domain}`;

  // Check cache freshness
  const cached = await chrome.storage.local.get(key);
  if (cached[key] && cached[key]._cachedAt &&
      Date.now() - cached[key]._cachedAt < CACHE_TTL_MS) {
    applyBadge(cached[key], tabId);
    notifyContent(cached[key], tabId);
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/site/${domain}`, {
      signal: AbortSignal.timeout(10000),
    });

    if (resp.ok) {
      const data = await resp.json();
      data._cachedAt = Date.now();
      await chrome.storage.local.set({ [key]: data });
      applyBadge(data, tabId);
      notifyContent(data, tabId);
    } else {
      const err = await resp.json().catch(() => ({}));
      const errData = { error: true, domain, message: err.message || "Not in database", _cachedAt: Date.now() };
      await chrome.storage.local.set({ [key]: errData });
      clearBadge(tabId);
    }
  } catch {
    clearBadge(tabId);
  }
}

function applyBadge(data, tabId) {
  if (!data || data.error) { clearBadge(tabId); return; }
  const sem   = data.site?.semaphore || "orange";
  const score = data.site?.semaphore_score ?? "";
  const color = BADGE_COLOR[sem] || BADGE_COLOR.orange;
  chrome.action.setBadgeText({ text: String(score), tabId });
  chrome.action.setBadgeBackgroundColor({ color, tabId });
}

function clearBadge(tabId) {
  chrome.action.setBadgeText({ text: "", tabId });
}

function notifyContent(data, tabId) {
  if (!data || data.error || !tabId) return;
  chrome.tabs.sendMessage(tabId, { type: "LEXIA_DATA", data }).catch(() => {});
}

async function onTabChange(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab?.url) return;
    const domain = extractDomain(tab.url);
    if (!domain) return;
    await fetchAndStore(domain, tabId);
  } catch {}
}

chrome.tabs.onActivated.addListener(({ tabId }) => onTabChange(tabId));
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "complete") onTabChange(tabId);
});

// Content script requests popup open after clicking the banner CTA
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "PAGE_LOADED") {
    const domain = extractDomain(msg.href);
    if (domain && sender.tab?.id) fetchAndStore(domain, sender.tab.id);
  }
  if (msg.type === "OPEN_POPUP") {
    // Chrome 127+: open popup programmatically
    if (chrome.action.openPopup) {
      chrome.action.openPopup().catch(() => {});
    }
  }
});
