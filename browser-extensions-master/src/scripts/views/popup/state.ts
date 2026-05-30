import { getLocal, setLocal } from '../../lib/chromeStorage';

export interface PopupPreferences {
    darkmode: boolean;
}

export async function hydrateState(): Promise<PopupPreferences> {
    const result = await getLocal(['darkmode']);
    return { darkmode: Boolean(result['darkmode']) };
}

export async function toggleDarkmode(): Promise<void> {
    const result = await getLocal(['darkmode']);
    await setLocal({ darkmode: !Boolean(result['darkmode']) });
}
