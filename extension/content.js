/**
 * LEXIA content script — minimal; signals the background worker to refresh
 * data for this page on load. No DOM mutation.
 */
chrome.runtime.sendMessage({ type: "PAGE_LOADED", href: window.location.href });
