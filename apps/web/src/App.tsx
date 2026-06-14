import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { WorkflowListPage } from "./pages/WorkflowListPage";
import { WorkflowCanvasPage } from "./pages/WorkflowCanvasPage";
import { ExecutionViewerPage } from "./pages/ExecutionViewerPage";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Protected() {
  return (
    <RequireAuth>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/workflows" element={<WorkflowListPage />} />
          <Route path="/workflows/new" element={<WorkflowCanvasPage />} />
          <Route path="/workflows/:id" element={<WorkflowCanvasPage />} />
          <Route path="/instances/:id" element={<ExecutionViewerPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<Protected />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
}
