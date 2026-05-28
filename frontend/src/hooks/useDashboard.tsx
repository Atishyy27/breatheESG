import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface DashboardData {
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
  pipeline?: {
    uploaded: number;
    parsed: number;
    normalized: number;
    validated: number;
    pending: number;
    approved: number;
  };
}

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard-analytics'],
    queryFn: async () => {
      // The trailing slash is critical for Django routing
      const res = await api.get('/dashboard/');
      return res.data;
    },
    refetchInterval: 30000, // Background poll every 30 seconds
  });
}