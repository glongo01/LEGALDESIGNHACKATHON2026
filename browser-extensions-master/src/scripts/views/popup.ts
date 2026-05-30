import { hydrateState, toggleDarkmode } from './popup/state';
import { initializePopupFromLocation } from './popup/navigation';

void (async function initPopup(): Promise<void> {
    await waitForDomReady();

    const prefs = await hydrateState();
    if (prefs.darkmode) {
        document.body.classList.add('dark-mode');
    }

    // dark mode toggle button
    const toggleBtn = document.getElementById('toggleButton');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', async () => {
            document.body.classList.toggle('dark-mode');
            await toggleDarkmode();
        });
    }

    await initializePopupFromLocation(window.location.href);
})();

async function waitForDomReady(): Promise<void> {
    if (document.readyState !== 'loading') return;
    await new Promise<void>((resolve) => {
        document.addEventListener('DOMContentLoaded', () => resolve(), { once: true });
    });
}
