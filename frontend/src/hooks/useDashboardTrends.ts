import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

export interface MonthlyPoint {
  period: string
  SCOPE_1: number
  SCOPE_2: number
  SCOPE_3: number
  total: number
}

export interface FYPoint {
  fy: string
  SCOPE_1: number
  SCOPE_2: number
  SCOPE_3: number
  total: number
}

export interface ActivityRow {
  activity_type: string
  total: number
  count: number
}

export interface AnomalyRow {
  anomaly_code: string
  count: number
}

export interface TrendsData {
  monthly: MonthlyPoint[]
  fy_comparison: FYPoint[]
  mom_change: number | null
  activity_breakdown: ActivityRow[]
  anomaly_distribution: AnomalyRow[]
  facility_monthly: Record<string, number | string>[]
  top_facility_codes: string[]
}

export function useDashboardTrends() {
  return useQuery<TrendsData>({
    queryKey: ['dashboard-trends'],
    queryFn: () => apiClient.get('/dashboard/trends/').then(r => r.data),
    refetchInterval: 60000,
    staleTime: 30000,
  })
}