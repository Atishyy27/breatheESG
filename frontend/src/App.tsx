import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

import { AppShell } from '@/components/layout/AppShell';
import { DashboardPage } from '@/pages/DashboardPage';
import { UploadsPage } from '@/pages/UploadsPage';
import { ReviewQueuePage } from '@/pages/ReviewQueuePage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { AuditPage } from '@/pages/AuditPage';
import { RoleProvider, useRole } from '@/context/RoleContext';
import { RoleSelectPage } from '@/pages/RoleSelectPage';
import { DatasetStudioPage } from '@/pages/DatasetStudioPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RoleProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
      </RoleProvider>
    </QueryClientProvider>
  );
}

function AppRoutes() {
  const { isAuthenticated } = useRole();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="*" element={<RoleSelectPage />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="uploads" element={<UploadsPage />} />
        <Route path="review" element={<ReviewQueuePage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="generate" element={<DatasetStudioPage />} />
        <Route path="select-role" element={<RoleSelectPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}