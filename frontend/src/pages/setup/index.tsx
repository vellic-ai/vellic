import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Wordmark, Spinner } from "@/components/icons";
import { useAuthStatus, useSetup, useLogin } from "@/api";
import { cn } from "@/lib/utils";

export default function SetupPage() {
  const navigate = useNavigate();
  const { data: authStatus, isLoading } = useAuthStatus();
  const setup = useSetup();
  const login = useLogin();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  if (isLoading) return null;
  if (!authStatus?.setup_required) return <Navigate to="/login" replace />;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || !confirm) return;
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError("");
    setup.mutate(
      { password },
      {
        onSuccess: () => {
          login.mutate(
            { password },
            {
              onSuccess: () => navigate("/dashboard", { replace: true }),
              onError: (err) => setError(err.message || "Login failed after setup."),
            },
          );
        },
        onError: (err) => setError(err.message || "Setup failed."),
      },
    );
  };

  const isPending = setup.isPending || login.isPending;

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="w-full max-w-[380px]">
        <div className="flex justify-center mb-6">
          <Wordmark size={28} />
        </div>

        <h1 className="sr-only">Vellic Setup</h1>

        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-border rounded p-7"
        >
          <p className="text-sm text-text-muted mb-5">
            Set an admin password to get started.
          </p>

          <div className="mb-[18px]">
            <label
              htmlFor="password"
              className="block text-sm text-text-muted font-medium mb-1.5"
            >
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoFocus
              placeholder="Choose a password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              className={cn(error && "border-error focus:border-error")}
            />
          </div>

          <div className="mb-[18px]">
            <label
              htmlFor="confirm"
              className="block text-sm text-text-muted font-medium mb-1.5"
            >
              Confirm password
            </label>
            <Input
              id="confirm"
              type="password"
              placeholder="Repeat password"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value);
                setError("");
              }}
              aria-describedby={error ? "confirm-error" : undefined}
              className={cn(error && "border-error focus:border-error")}
            />
            {error && (
              <p id="confirm-error" className="text-error text-xs mt-1.5" role="alert">
                {error}
              </p>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={!password || !confirm || isPending}
          >
            {isPending && <Spinner size={14} />}
            Set password &amp; continue
          </Button>
        </form>

        <p className="text-center mt-4 text-xs text-text-muted">
          Self-hosted instance · v0.4.2
        </p>
      </div>
    </div>
  );
}
