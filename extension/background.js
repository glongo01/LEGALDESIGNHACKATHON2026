/**
 * LEXIA service worker — fetches compliance data for the active tab's domain
 * and stores it in chrome.storage.local keyed by domain.
 */

const API_BASE = "http://localhost:5050";
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

function extractDomain(url) {
  try {
    const u = new URL(url);
    if (!["http:", "https:"].includes(u.protocol)) return null;
    return u.hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

async function fetchAndStore(domain) {
  const key = `lexia:${domain}`;

  // Check cache freshness
  const cached = await chrome.storage.local.get(key);
  if (cached[key] && cached[key]._cachedAt) {
    if (Date.now() - cached[key]._cachedAt < CACHE_TTL_MS) {
      return; // still fresh
    }
  }

  try {
    const resp = await fetch(`${API_BASE}/api/site/${domain}`, {
      signal: AbortSignal.timeout(10000),
    });

    if (resp.ok) {
      const data = await resp.json();
      data._cachedAt = Date.now();
      await chrome.storage.local.set({ [key]: data });
    } else {
      const err = await resp.json().catch(() => ({}));
      await chrome.storage.local.set({
        [key]: { error: true, domain, message: err.message || "Not in database", _cachedAt: Date.now() },
      });
    }
  } catch (e) {
    await chrome.storage.local.set({
      [key]: { error: true, domain, message: "Backend unavailable — start the API server", _cachedAt: Date.now() },
    });
  }
}

async function onTabChange(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab || !tab.url) return;
    const domain = extractDomain(tab.url);
    if (!domain) return;
    await fetchAndStore(domain);
  } catch {
    // tab may have been closed
  }
}

chrome.tabs.onActivated.addListener(({ tabId }) => onTabChange(tabId));

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "complete") onTabChange(tabId);
});
