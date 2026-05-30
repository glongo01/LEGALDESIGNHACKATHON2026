import { DEFAULT_POPUP_PATH } from '../constants';
import type { Service } from './types';

export function setPopup(
    tabId: number | undefined | null,
    popup: string = DEFAULT_POPUP_PATH
): void {
    if (typeof tabId !== 'number') {
        chrome.action.setPopup({ popup });
        return;
    }
    chrome.action.setPopup({ tabId, popup });
}

export function setTabIcon(
    tab: chrome.tabs.Tab | null | undefined,
    icon: string
): void {
    const iconDetails: chrome.action.TabIconDetails = {
        path: {
            32:  `/icons/${icon}/${icon}32.png`,
            48:  `/icons/${icon}/${icon}48.png`,
            128: `/icons/${icon}/${icon}128.png`,
        },
    };

    if (tab?.id) {
        iconDetails.tabId = tab.id;
    }

    chrome.action.setIcon(iconDetails);
}

/** Called when a matching service is found in the DB. */
export async function serviceDetected(
    tab: chrome.tabs.Tab,
    service: Service
): Promise<void> {
    // icon name matches semaphore: "red" | "yellow" | "green"
    setTabIcon(tab, service.rating);
    setPopup(tab.id, `${DEFAULT_POPUP_PATH}?service-id=${service.id}`);
}
