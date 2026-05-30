/**
 * service.ts
 * ──────────
 * Renders a matched service entry from the bundled DB into the popup UI.
 * No network calls — everything comes from the static db.json.
 */

import { BUNDLED_DB } from '../../background/database';
import type { DatabaseEntry, Finding, Semaphore } from '../../background/types';

// ── Public entry point ────────────────────────────────────────────────────────

export function displayServiceFromDb(id: string): void {
    const entry = BUNDLED_DB.find((e) => e.id === id);

    if (!entry) {
        showError('Service not found in database.', `id: ${id}`);
        return;
    }

    renderService(entry);
}

// ── Renderer ──────────────────────────────────────────────────────────────────

function renderService(entry: DatabaseEntry): void {
    setServiceName(entry.name);
    setSemaphore(entry.rating);
    populateFindings(entry.findings);
    revealLoaded();
}

function setServiceName(name: string): void {
    document.querySelectorAll<HTMLElement>('.serviceName').forEach((el) => {
        el.innerText = name;
    });
}

function setSemaphore(rating: Semaphore): void {
    const header = document.getElementById('headerPopup');
    const light  = document.getElementById('semaphoreLight');
    const label  = document.getElementById('semaphoreLabel');

    if (header) {
        header.classList.remove('red', 'yellow', 'green');
        header.classList.add(rating);
    }

    const config: Record<Semaphore, { emoji: string; text: string }> = {
        red:    { emoji: '🔴', text: 'Prohibited practice detected' },
        yellow: { emoji: '🟡', text: 'High-risk AI — verify your rights' },
        green:  { emoji: '🟢', text: 'Transparency obligations appear met' },
    };

    if (light)  light.innerText  = config[rating].emoji;
    if (label)  label.innerText  = config[rating].text;
}

function populateFindings(findings: Finding[]): void {
    const prohibitions = findings.filter((f) => f.type === 'prohibition' && f.classification !== 'background');
    const rights       = findings.filter((f) => f.type === 'right'       && f.classification === 'explicit');
    const gaps         = findings.filter((f) => f.type === 'right'       && f.classification === 'background');

    renderGroup('prohibitionList', prohibitions, 'prohibition');
    renderGroup('rightsList',      rights,       'right');
    renderGroup('gapsList',        gaps,         'gap');

    // hide empty sections
    toggleSection('prohibitionSection', prohibitions.length > 0);
    toggleSection('rightsSection',      rights.length > 0);
    toggleSection('gapsSection',        gaps.length > 0);
}

function renderGroup(containerId: string, findings: Finding[], kind: string): void {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    findings.forEach((f, i) => {
        const item = document.createElement('div');
        item.className = `finding ${kind}`;
        item.innerHTML = `
            <div class="finding-header">
                <span class="finding-concept">${escapeHtml(f.concept)}</span>
                <span class="finding-article">${escapeHtml(f.article)}</span>
            </div>
            <p class="finding-summary">${escapeHtml(f.summary)}</p>
        `.trim();
        container.appendChild(item);

        if (i < findings.length - 1) {
            const hr = document.createElement('hr');
            container.appendChild(hr);
        }
    });
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function revealLoaded(): void {
    hide('loading');
    const loaded = document.getElementById('loaded');
    if (loaded) loaded.style.filter = 'none';
}

function toggleSection(id: string, visible: boolean): void {
    const el = document.getElementById(id);
    if (el) el.style.display = visible ? 'block' : 'none';
}

function hide(id: string): void {
    const el = document.getElementById(id);
    if (el) {
        el.style.opacity = '0';
        setTimeout(() => { el.style.display = 'none'; }, 200);
    }
}

function showError(title: string, description: string): void {
    hide('loading');
    const errorEl      = document.getElementById('error');
    const titleEl      = document.getElementById('errorTitle');
    const descriptionEl = document.getElementById('errorDescription');
    if (titleEl)       titleEl.innerText = title;
    if (descriptionEl) descriptionEl.innerText = description;
    if (errorEl)       errorEl.style.display = 'flex';
}

export function showNotFound(domain: string): void {
    hide('loading');
    hide('loaded');
    const notFound = document.getElementById('nourl');
    if (notFound) notFound.style.display = 'block';
    const domainEl = document.getElementById('notFoundDomain');
    if (domainEl) domainEl.innerText = domain;
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
