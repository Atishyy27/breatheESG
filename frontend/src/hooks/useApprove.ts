import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'

interface ApprovePayload {
  id: number
  bypass_validation: boolean
  review_notes: string
}

export function useApprove() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, bypass_validation, review_notes }: ApprovePayload) => {
      const response = await apiClient.post(`/review/${id}/approve/`, {
        bypass_validation,
        review_notes,
      })
      return response.data
    },
    onSuccess: () => {
      toast.success('Record approved and locked for audit')
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-trends'] })
      queryClient.invalidateQueries({ queryKey: ['audit-ledger'] })
    },
    onError: (err: any) => {
      toast.error('Approval failed', {
        description: err.response?.data?.error || 'Unknown error occurred',
      })
    },
  })
}