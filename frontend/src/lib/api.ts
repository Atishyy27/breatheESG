import axios from 'axios'
import type { Activity, DashboardMetrics, UploadSummary } from '@/types'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'X-Analyst-Email': 'analyst@breatheesg.com',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const api = {
  // Raw passthrough (used by pages calling api.get / api.post directly)
  get: (url: string, config?: any) => apiClient.get(url, config),
  post: (url: string, data?: any, config?: any) => apiClient.post(url, data, config),

  // Dashboard
  getDashboardStats: () =>
    apiClient.get<DashboardMetrics>('/dashboard/').then((r) => r.data),

  // Uploads
  getUploads: () =>
    apiClient.get<UploadSummary[]>('/uploads/').then((r) => r.data),

  uploadFile: (file: File, sourceType: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_type', sourceType)
    return apiClient
      .post('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  // Review Queue
  getReviewQueue: () =>
    apiClient.get<Activity[]>('/review/').then((r) => r.data),

  getActivityDetail: (id: number) =>
    apiClient.get<Activity>(`/review/${id}/`).then((r) => r.data),

  // Actions
  approveActivity: (id: number, bypass: boolean, notes: string) =>
    apiClient
      .post(`/review/${id}/approve/`, {
        bypass_validation: bypass,
        review_notes: notes,
      })
      .then((r) => r.data),

  rejectActivity: (id: number) =>
    apiClient.post(`/review/${id}/reject/`).then((r) => r.data),

  batchApprove: (ids: number[]) =>
    apiClient
      .post('/review/batch-approve/', { activity_ids: ids })
      .then((r) => r.data),
}