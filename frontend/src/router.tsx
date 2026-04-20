import { createBrowserRouter } from "react-router";
import LoginPage from "@/pages/LoginPage";
import NotFoundPage from "@/pages/NotFoundPage";
import DesignShowcase from "@/pages/design-showcase";

const routes = [
  {
    path: "/",
    element: <LoginPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
];

if (import.meta.env.DEV) {
  routes.splice(-1, 0, { path: "/__/design", element: <DesignShowcase /> });
}

export const router = createBrowserRouter(routes);
