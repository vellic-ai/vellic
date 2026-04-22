import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { ToastRoot } from "@/lib/toast";
import AuthGuard from "@/components/AuthGuard";
import AuthPage from "@/pages/auth";
import SetupPage from "@/pages/setup";
import DashboardPage from "@/pages/dashboard";
import DeliveriesPage from "@/pages/deliveries";
import JobsPage from "@/pages/jobs";
import SettingsPage from "@/pages/settings";
import ReposPage from "@/pages/repos";
import RepoExtensionsPage from "@/pages/repo-extensions";
import FeatureFlagsPage from "@/pages/feature-flags";
import NotFoundPage from "@/pages/NotFoundPage";
import DesignShowcase from "@/pages/design-showcase";

// eslint-disable-next-line react-refresh/only-export-components
function AppRoot() {
  return (
    <ToastRoot>
      <Outlet />
    </ToastRoot>
  );
}

const routes = [
  {
    element: <AppRoot />,
    children: [
      { path: "/login", element: <AuthPage /> },
      { path: "/setup", element: <SetupPage /> },
      {
        path: "/",
        element: (
          <AuthGuard>
            <Navigate to="/dashboard" replace />
          </AuthGuard>
        ),
      },
      {
        path: "/dashboard",
        element: (
          <AuthGuard>
            <DashboardPage />
          </AuthGuard>
        ),
      },
      {
        path: "/deliveries",
        element: (
          <AuthGuard>
            <DeliveriesPage />
          </AuthGuard>
        ),
      },
      {
        path: "/jobs",
        element: (
          <AuthGuard>
            <JobsPage />
          </AuthGuard>
        ),
      },
      {
        path: "/jobs/:jobId",
        element: (
          <AuthGuard>
            <JobsPage />
          </AuthGuard>
        ),
      },
      {
        path: "/settings",
        element: (
          <AuthGuard>
            <SettingsPage />
          </AuthGuard>
        ),
      },
      {
        path: "/repos",
        element: (
          <AuthGuard>
            <ReposPage />
          </AuthGuard>
        ),
      },
      {
        path: "/repos/:repoId/extensions",
        element: (
          <AuthGuard>
            <RepoExtensionsPage />
          </AuthGuard>
        ),
      },
      {
        path: "/feature-flags",
        element: (
          <AuthGuard>
            <FeatureFlagsPage />
          </AuthGuard>
        ),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

if (import.meta.env.DEV) {
  routes[0].children.splice(-1, 0, {
    path: "/__/design",
    element: <DesignShowcase />,
  });
}

export const router = createBrowserRouter(routes);
