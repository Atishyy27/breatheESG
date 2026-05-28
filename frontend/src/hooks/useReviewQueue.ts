import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

export interface QueueItem {
  id: number
  source_type: string
  activity_type: string
  activity_date: string
  reporting_period: string
  facility_code: string | null
  quantity: number | null
  unit: string
  co2e_kg: number
  review_status: 'PENDING' | 'SUSPICIOUS' | 'APPROVED'
  anomaly_code: string | null
  anomaly_details: string | null
  inline_issues: string[]
}

export function useReviewQueue() {
  return useQuery<QueueItem[]>({
    queryKey: ['review-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/review/')
      return response.data
    },
    refetchInterval: 15000,
  })
}