import { createBrowserRouter, Outlet } from "react-router";
import { ToastRoot } from "@/lib/toast";
import AuthPage from "@/pages/auth";
import DashboardPage from "@/pages/dashboard";
import DeliveriesPage from "@/pages/deliveries";
import JobsPage from "@/pages/jobs";
import SettingsPage from "@/pages/settings";
import ReposPage from "@/pages/repos";
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
      { path: "/", element: <DashboardPage /> },
      { path: "/deliveries", element: <DeliveriesPage /> },
      { path: "/jobs", element: <JobsPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/repos", element: <ReposPage /> },
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
