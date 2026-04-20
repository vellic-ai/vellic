import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-bg">
      <p className="text-text-muted text-sm">404 — Page not found</p>
      <Button variant="ghost" asChild>
        <a href="/">Go home</a>
      </Button>
    </div>
  );
}
