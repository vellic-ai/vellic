import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { Icons } from "@/components/icons";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "info" | "warning";

interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastApi {
  success: (msg: string) => void;
  error: (msg: string) => void;
  info: (msg: string) => void;
}

const ToastCtx = React.createContext<ToastApi | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastApi {
  const ctx = React.useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used inside ToastRoot");
  return ctx;
}

export function ToastRoot({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const push = React.useCallback((message: string, variant: ToastVariant) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, variant }]);
  }, []);

  const api = React.useMemo<ToastApi>(
    () => ({
      success: (m) => push(m, "success"),
      error: (m) => push(m, "error"),
      info: (m) => push(m, "info"),
    }),
    [push],
  );

  const remove = (id: string) =>
    setToasts((t) => t.filter((x) => x.id !== id));

  return (
    <ToastCtx.Provider value={api}>
      <ToastPrimitive.Provider duration={4000}>
        {children}
        {toasts.map((t) => (
          <ToastPrimitive.Root
            key={t.id}
            onOpenChange={(open) => !open && remove(t.id)}
            className={cn(
              "pointer-events-auto flex items-start gap-2.5",
              "min-w-[260px] max-w-[360px] rounded border border-border bg-surface",
              "shadow-[0_6px_18px_rgba(0,0,0,0.35)] p-3 pr-3.5 border-l-[3px]",
              "animate-toast-in",
              {
                "border-l-success": t.variant === "success",
                "border-l-error": t.variant === "error",
                "border-l-accent": t.variant === "info",
                "border-l-warning-border": t.variant === "warning",
              },
            )}
          >
            <span
              className={cn("mt-0.5 inline-flex shrink-0", {
                "text-success": t.variant === "success",
                "text-error": t.variant === "error",
                "text-accent": t.variant === "info",
                "text-warning-text": t.variant === "warning",
              })}
            >
              {t.variant === "success" ? (
                <Icons.check size={14} />
              ) : t.variant === "error" ? (
                <Icons.warn size={14} />
              ) : (
                <Icons.info size={14} />
              )}
            </span>
            <ToastPrimitive.Description className="flex-1 text-sm text-text">
              {t.message}
            </ToastPrimitive.Description>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none w-[min(360px,calc(100vw-32px))]" />
      </ToastPrimitive.Provider>
    </ToastCtx.Provider>
  );
}
