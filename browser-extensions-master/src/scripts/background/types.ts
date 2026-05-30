export type Semaphore = 'red' | 'yellow' | 'green';

export type FindingType = 'right' | 'prohibition';
export type FindingClassification = 'explicit' | 'implicit' | 'background';

export interface Finding {
    concept: string;          // e.g. "ChatbotDisclosure", "BiometricSystem"
    article: string;          // e.g. "Art. 52(1) AIA"
    summary: string;
    type: FindingType;
    classification: FindingClassification;
}

export interface DatabaseEntry {
    id: string;
    name: string;
    url: string;              // comma-separated domains
    rating: Semaphore;
    findings: Finding[];
}

export interface Service {
    id: string;
    name: string;
    rating: Semaphore;
    findings: Finding[];
}
