import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

export function useUploads() {
  const queryClient = useQueryClient();

  const history = useQuery({
    queryKey: ['uploads-history'],
    queryFn: async () => {
      const response = await api.get('/uploads/');
      return response.data;
    },
    refetchInterval: 15000, // Background poll every 15s
  });

  const upload = useMutation({
    mutationFn: ({ file, type }: { file: File; type: string }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', type);
      return api.post('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
    onSuccess: (response) => {
      const stats = response.data.upload_details;
      toast.success('Ingestion Sequence Complete', {
        description: `Parsed: ${stats?.total_records} | Normalized: ${stats?.successfully_normalized} | Errors: ${stats?.validation_errors_found}`,
      });
      queryClient.invalidateQueries({ queryKey: ['uploads-history'] });
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
    },
    onError: (err: any) => {
      toast.error('Pipeline Rejected', {
        description: err.response?.data?.error || 'A fatal validation error occurred.',
      });
    }
  });

  return { history, upload };
}