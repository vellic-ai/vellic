import { Navigate } from "react-router";
import { Spinner } from "@/components/icons";
import { useAuthStatus } from "@/api";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useAuthStatus();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <Spinner size={20} />
      </div>
    );
  }

  if (data?.setup_required) return <Navigate to="/setup" replace />;
  if (!data?.authenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
