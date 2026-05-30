import { displayServiceFromDb, showNotFound } from './service';

export async function initializePopupFromLocation(locationHref: string): Promise<void> {
    const serviceId = extractParam(locationHref, 'service-id');

    if (serviceId) {
        displayServiceFromDb(serviceId);
        return;
    }

    const domain = extractParam(locationHref, 'url');
    showNotFound(domain ?? 'this site');
}

function extractParam(href: string, key: string): string | undefined {
    const match = href.split(`?${key}=`)[1];
    return match ? match.replace('#', '') : undefined;
}
