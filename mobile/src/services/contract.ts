export interface Identification {
  predicted_species: string;
  common_name: string;
  sdp_listed_invasive: boolean;
  confidence: number;
  uncertain_identification: boolean;
  known_class_scope_only: true;
  supported_species_count: number;
}

export function parseIdentification(value: unknown): Identification {
  if (!value || typeof value !== 'object') throw new Error('Invalid result');
  const result = value as Partial<Identification>;
  if (
    typeof result.predicted_species !== 'string' || !result.predicted_species.trim() ||
    typeof result.common_name !== 'string' || !result.common_name.trim() ||
    typeof result.sdp_listed_invasive !== 'boolean' ||
    typeof result.confidence !== 'number' || !Number.isFinite(result.confidence) ||
    result.confidence < 0 || result.confidence > 1 ||
    typeof result.uncertain_identification !== 'boolean' ||
    result.known_class_scope_only !== true ||
    !Number.isInteger(result.supported_species_count) ||
    (result.supported_species_count ?? 0) < 1
  ) throw new Error('Invalid result');
  return result as Identification;
}

export function resolveApiUrl(override?: string, developmentHost?: string): string {
  if (override?.trim()) return override.trim().replace(/\/+$/, '');
  if (developmentHost) {
    const host = developmentHost.split(':')[0];
    if (/^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$/.test(host)) {
      return 'http://' + host + ':8000';
    }
  }
  return 'http://127.0.0.1:8000';
}
