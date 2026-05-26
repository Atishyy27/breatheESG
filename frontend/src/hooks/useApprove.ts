import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface ApprovePayload {
  id: number
  bypass_validation: boolean
  review_notes: string
}

export function useApprove() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, bypass_validation, review_notes }: ApprovePayload) => {
      const response = await api.post(`/review/${id}/approve/`, {
        bypass_validation,
        review_notes
      })
      return response.data
    },
    onSuccess: () => {
      // Invalidate states synchronously to drive instant dashboard layout updates
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['upload-history'] })
    }
  })
}
