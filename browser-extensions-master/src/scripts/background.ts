import { checkIfUpdateNeeded } from './background/database';
import { handleExtensionInstalled } from './background/install';
import { initializePageAction } from './background/pageAction';

chrome.action.setBadgeText({ text: '' });

// load bundled DB into storage on every startup so pageAction can read it fast
chrome.runtime.onStartup.addListener(() => {
    void checkIfUpdateNeeded();
});

chrome.runtime.onInstalled.addListener(() => {
    void handleExtensionInstalled();
});

chrome.tabs.onUpdated.addListener((_, changeInfo, tab) => {
    if (changeInfo.status === 'complete') {
        void initializePageAction(tab);
    }
});

chrome.tabs.onCreated.addListener((tab) => {
    void initializePageAction(tab);
});

chrome.tabs.onActivated.addListener((activeInfo) => {
    chrome.tabs.get(activeInfo.tabId, (tab) => {
        void initializePageAction(tab);
    });
});
