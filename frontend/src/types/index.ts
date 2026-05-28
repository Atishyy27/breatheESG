// src/types/index.ts

export type ActivityScope = 'SCOPE_1' | 'SCOPE_2' | 'SCOPE_3';
export type ReviewStatus = 'PENDING' | 'SUSPICIOUS' | 'APPROVED' | 'REJECTED';
export type IssueSeverity = 'ERROR' | 'WARNING';
export type UploadStatus = 'UPLOADED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface ValidationIssue {
  severity: IssueSeverity;
  issue_type: string;
  message: string;
}

export interface RawRecord {
  line_number: number;
  raw_data: Record<string, any>;
}

export interface Activity {
  id: number;
  scope: ActivityScope;
  scope_category: string;
  activity_type: string;
  activity_date: string;
  reporting_period: string;
  facility_code: string | null;
  quantity: number | null;
  unit: string;
  factor_value_used: string | number; // Handled as string to preserve decimal precision from DB
  emission_factor_source: string;
  co2e_kg: number;
  review_status: ReviewStatus;
  anomaly_code: string | null;
  anomaly_details: string | null;
  inline_issues?: string[]; // Synthesized for the queue view
  
  // Relations populated on detail view
  raw_line_number?: number;
  raw_record_data?: Record<string, any>;
  validation_issues?: ValidationIssue[];
  created_at?: string;
  reviewed_at?: string | null;
  reviewed_by_email?: string | null;
}

export interface UploadSummary {
  id: number;
  filename: string;
  source_type: string;
  status: UploadStatus;
  total_rows: number;
  normalized_rows: number;
  error_rows: number;
  warning_rows: number;
  suspicious_rows: number;
  uploaded_at: string;
}

export interface DashboardMetrics {
  total_co2e: number;
  scope_1: number;
  scope_2: number;
  scope_3: number;
  pending_count: number;
  suspicious_count: number;
  success_rate: number;
  total_uploads: number;
  top_facilities: Array<{
    code: string;
    name: string;
    co2e: number;
    percent: number;
  }>;
}