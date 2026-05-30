// donation features removed in AI Act Checker fork
export async function checkDonationReminder(): Promise<void> { /* no-op */ }
export function donationReminderAllowed(_userAgent: string): boolean { return false; }
