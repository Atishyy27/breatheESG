/**
 * Global Constants & Mappers for BreatheESG Workbench
 */

export const FACILITY_NAMES: Record<string, string> = {
  'IN01': 'Mumbai Manufacturing Plant',
  'DE02': 'Frankfurt Distribution Center',
  'US03': 'Austin Operations Hub',
  'CN04': 'Shanghai Assembly Facility',
  'BR05': 'São Paulo Warehouse',
  'IN02': 'Bangalore Tech Center',
};

/**
 * Safely resolves a facility code to its human-readable name.
 */
export function getFacilityName(code: string | null | undefined): string {
  if (!code) return 'Unallocated Infrastructure';
  return FACILITY_NAMES[code] || 'Specialized Operations Node';
}

/**
 * Maps system anomaly codes to user-friendly UI labels
 */
export const ANOMALY_LABELS: Record<string, string> = {
  'QUANTITY_SPIKE': '⚠ Spike Detected',
  'NEGATIVE_VALUE': '✗ Negative Value',
  'MISSING_FACILITY': '⚠ Unknown Facility',
  'FUTURE_DATE': '⚠ Future Date',
};