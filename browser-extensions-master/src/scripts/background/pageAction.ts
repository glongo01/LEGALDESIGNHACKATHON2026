import { ALLOWED_PROTOCOLS, DEFAULT_POPUP_PATH } from '../constants';
import type { DatabaseEntry } from './types';
import { findServiceMatch } from './serviceDetection';
import { serviceDetected, setPopup, setTabIcon } from './tabUi';
import { BUNDLED_DB, loadBundledDatabase } from './database';
import { getLocal } from '../lib/chromeStorage';

export async function initializePageAction(
    tab?: chrome.tabs.Tab | null
): Promise<void> {
    if (!tab || !tab.url) {
        setPopup(null, DEFAULT_POPUP_PATH);
        setTabIcon(tab, 'logo');
        return;
    }

    let parsedUrl: URL;
    try {
        parsedUrl = new URL(tab.url);
    } catch (error) {
        console.error('Invalid URL for tab', error);
        setPopup(tab.id, DEFAULT_POPUP_PATH);
        setTabIcon(tab, 'logo');
        return;
    }

    if (!isAllowedProtocol(parsedUrl.protocol)) {
        setPopup(tab.id, DEFAULT_POPUP_PATH);
        setTabIcon(tab, 'logo');
        return;
    }

    setTabIcon(tab, 'loading');

    const db = await getDatabase();
    const { service, normalizedDomain } = findServiceMatch(parsedUrl.hostname, db);

    if (service) {
        await serviceDetected(tab, service);
        return;
    }

    setPopup(tab.id, `${DEFAULT_POPUP_PATH}?url=${normalizedDomain}`);
    setTabIcon(tab, 'notfound');
}

async function getDatabase(): Promise<DatabaseEntry[]> {
    // try storage cache first (populated on startup)
    const stored = await getLocal('db');
    const cached = stored['db'] as DatabaseEntry[] | undefined;
    if (cached && cached.length > 0) {
        return cached;
    }

    // fallback: reload from bundle and cache it
    await loadBundledDatabase();
    return BUNDLED_DB;
}

function isAllowedProtocol(protocol: string): boolean {
    return (ALLOWED_PROTOCOLS as readonly string[]).includes(protocol);
}
