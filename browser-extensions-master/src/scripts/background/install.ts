import { checkIfUpdateNeeded } from './database';
import { initializePageAction } from './pageAction';

export async function handleExtensionInstalled(): Promise<void> {
    await checkIfUpdateNeeded();

    const [activeTab] = await queryActiveTab();
    if (activeTab) {
        await initializePageAction(activeTab);
    }
}

async function queryActiveTab(): Promise<chrome.tabs.Tab[]> {
    return new Promise((resolve) => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            resolve(tabs);
        });
    });
}
