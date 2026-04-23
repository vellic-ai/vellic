import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Wordmark, Spinner } from "@/components/icons";
import { useLogin, useAuthStatus } from "@/api";
import { cn } from "@/lib/utils";

export default function AuthPage() {
  const navigate = useNavigate();
  const { data: authStatus } = useAuthStatus();
  const login = useLogin();

  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (authStatus?.authenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [authStatus?.authenticated, navigate]);

  if (authStatus?.setup_required) return <Navigate to="/setup" replace />;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setError("");
    login.mutate(
      { password },
      {
        onSuccess: () => navigate("/dashboard"),
        onError: (err) => setError(err.message || "Incorrect password."),
      },
    );
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="w-full max-w-[380px]">
        <div className="flex justify-center mb-4">
          <Wordmark size={28} />
        </div>

        <h1 className="sr-only">Vellic</h1>

        <p className="text-center text-xs text-text-muted mb-5">
          Single-admin instance — no username, password only
        </p>

        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-border rounded p-7"
        >
          <div className="mb-[18px]">
            <label
              htmlFor="password"
              className="block text-sm text-text-muted font-medium mb-1.5"
            >
              Admin password
            </label>
            <Input
              id="password"
              type="password"
              autoFocus
              placeholder="Enter password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              aria-describedby={error ? "password-error" : undefined}
              className={cn(error && "border-error focus:border-error")}
            />
            {error && (
              <p id="password-error" className="text-error text-xs mt-1.5" role="alert">
                {error}
              </p>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={!password || login.isPending}
          >
            {login.isPending && <Spinner size={14} />}
            Sign in
          </Button>
        </form>

        <p className="text-center mt-4 text-xs text-text-muted">
          Self-hosted instance · v0.4.2
        </p>
      </div>
    </div>
  );
}
