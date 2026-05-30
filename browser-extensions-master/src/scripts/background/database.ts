/**
 * database.ts
 * ───────────
 * Our extension ships with a bundled static database instead of fetching
 * from an external API. This keeps the extension self-contained and avoids
 * any network dependency at startup.
 *
 * To regenerate db.json after running the scraper + classifier:
 *   python build_db.py   (from the repo root)
 */

import { setLocal } from '../lib/chromeStorage';
import staticDb from '../../static/db.json';
import type { DatabaseEntry } from './types';

export const BUNDLED_DB: DatabaseEntry[] = staticDb as DatabaseEntry[];

/**
 * Write the bundled DB into chrome.storage.local so pageAction.ts
 * can read it without re-importing the JSON every time.
 */
export async function loadBundledDatabase(): Promise<void> {
    await setLocal({
        db: BUNDLED_DB,
        lastModified: new Date().toISOString(),
    });
}

/**
 * Called on extension install/startup. Always reloads from bundle
 * (no stale-check needed — the bundle updates with each extension version).
 */
export async function checkIfUpdateNeeded(): Promise<void> {
    await loadBundledDatabase();
}
