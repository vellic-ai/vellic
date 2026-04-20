/**
 * /__/design — dev-only design system showcase.
 * Shows every VEL-43 component mapped to its shadcn/ui equivalent.
 * Only mounted in development (see router config in App).
 */
import { Button }   from "@/components/ui/button";
import { Input }    from "@/components/ui/input";
import { Badge }    from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TableWrapper, Table, TableHeader, TableBody, TableRow, TableHead, TableCell }
  from "@/components/ui/table";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import {
  Dialog, DialogTrigger, DialogContent, DialogHeader, DialogBody, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import {
  ToastProvider, ToastViewport, Toast, ToastTitle, ToastDescription, ToastClose,
} from "@/components/ui/toast";
import { useState } from "react";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-xs font-medium uppercase tracking-widest text-text-muted mb-4 pb-2 border-b border-border">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap items-center gap-3">{children}</div>;
}

const SAMPLE_ROWS = [
  { id: "d-001", status: "success", repo: "acme/api",     ref: "main",   ts: "2m ago" },
  { id: "d-002", status: "error",   repo: "acme/worker",  ref: "feat/x", ts: "14m ago" },
  { id: "d-003", status: "default", repo: "acme/frontend",ref: "main",   ts: "1h ago" },
];

export default function DesignShowcase() {
  const [toastOpen, setToastOpen] = useState(false);
  const [toastVariant, setToastVariant] = useState<"success"|"error"|"info">("info");

  function fireToast(v: typeof toastVariant) {
    setToastVariant(v);
    setToastOpen(false);
    setTimeout(() => setToastOpen(true), 50);
  }

  return (
    <ToastProvider>
      <div className="min-h-screen bg-bg text-text font-sans text-base p-8 max-w-5xl mx-auto">
        <header className="mb-10">
          <h1 className="text-lg font-semibold mb-1">vellic design system</h1>
          <p className="text-sm text-text-muted">
            VEL-43 → Tailwind v4 + shadcn/ui mapping. Dev-only showcase at <code className="font-mono">/__/design</code>.
          </p>
        </header>

        {/* ── Buttons ── */}
        <Section title="Button">
          <Row>
            <Button variant="default">Default</Button>
            <Button variant="primary">Primary</Button>
            <Button variant="danger">Danger</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="outline">Outline</Button>
          </Row>
          <Row>
            <Button variant="primary" size="sm">Small</Button>
            <Button variant="primary" size="default">Default</Button>
            <Button variant="primary" size="lg">Large</Button>
            <Button variant="primary" disabled>Disabled</Button>
          </Row>
        </Section>

        {/* ── Badges ── */}
        <Section title="Badge">
          <Row>
            <Badge variant="default">Default</Badge>
            <Badge variant="success">
              <span className="w-1.5 h-1.5 rounded-full bg-success inline-block" />
              Success
            </Badge>
            <Badge variant="error">Error</Badge>
            <Badge variant="warning">Warning</Badge>
            <Badge variant="info">Info</Badge>
          </Row>
        </Section>

        {/* ── Inputs ── */}
        <Section title="Input / Select">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
            <div>
              <label className="block text-sm text-text-muted mb-1.5 font-medium">Normal</label>
              <Input placeholder="Enter value…" />
            </div>
            <div>
              <label className="block text-sm text-text-muted mb-1.5 font-medium">Error</label>
              <Input placeholder="Invalid value" error />
              <p className="text-xs text-error mt-1.5">This field is required</p>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm text-text-muted mb-1.5 font-medium">Select</label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Choose provider…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="groq">Groq</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </Section>

        {/* ── Cards ── */}
        <Section title="Card">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader><CardTitle>Deliveries</CardTitle></CardHeader>
              <CardContent>
                <span className="text-2xl font-semibold">1,284</span>
                <p className="text-sm text-text-muted mt-1">Last 24 hours</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Errors</CardTitle></CardHeader>
              <CardContent>
                <span className="text-2xl font-semibold text-error">12</span>
                <p className="text-sm text-text-muted mt-1">Last 24 hours</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>P95 latency</CardTitle></CardHeader>
              <CardContent>
                <span className="text-2xl font-semibold">342ms</span>
                <p className="text-sm text-text-muted mt-1">Across all repos</p>
              </CardContent>
            </Card>
          </div>
        </Section>

        {/* ── Table ── */}
        <Section title="Table">
          <TableWrapper>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Repository</TableHead>
                  <TableHead>Ref</TableHead>
                  <TableHead>When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {SAMPLE_ROWS.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell><code className="font-mono text-text-muted">{r.id}</code></TableCell>
                    <TableCell>
                      <Badge variant={r.status as any}>{r.status}</Badge>
                    </TableCell>
                    <TableCell>{r.repo}</TableCell>
                    <TableCell><code className="font-mono text-sm">{r.ref}</code></TableCell>
                    <TableCell className="text-text-muted">{r.ts}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableWrapper>
        </Section>

        {/* ── Dialog ── */}
        <Section title="Dialog (Modal)">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="default">Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirm action</DialogTitle>
                <DialogDescription>This cannot be undone.</DialogDescription>
              </DialogHeader>
              <DialogBody>
                <p className="text-sm text-text-muted">
                  Are you sure you want to delete this webhook configuration?
                </p>
              </DialogBody>
              <DialogFooter>
                <Button variant="ghost">Cancel</Button>
                <Button variant="danger">Delete</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </Section>

        {/* ── Toast ── */}
        <Section title="Toast">
          <Row>
            <Button variant="default" size="sm" onClick={() => fireToast("success")}>
              Success toast
            </Button>
            <Button variant="default" size="sm" onClick={() => fireToast("error")}>
              Error toast
            </Button>
            <Button variant="default" size="sm" onClick={() => fireToast("info")}>
              Info toast
            </Button>
          </Row>
        </Section>

        {/* ── Color palette ── */}
        <Section title="Color tokens">
          <div className="flex flex-wrap gap-2">
            {[
              ["bg",           "var(--bg)"],
              ["surface",      "var(--surface)"],
              ["surface-2",    "var(--surface-2)"],
              ["border",       "var(--border)"],
              ["accent",       "var(--accent)"],
              ["danger",       "var(--danger)"],
              ["success",      "var(--success)"],
              ["error",        "var(--error)"],
              ["text-muted",   "var(--text-muted)"],
            ].map(([name, val]) => (
              <div key={name} className="flex flex-col items-center gap-1">
                <div className="w-10 h-10 rounded border border-border"
                     style={{ background: val }} />
                <span className="text-xs text-text-muted">{name}</span>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* Toast display */}
      <Toast open={toastOpen} onOpenChange={setToastOpen} variant={toastVariant}>
        <div className="flex-1">
          <ToastTitle>
            {toastVariant === "success" ? "Done!" : toastVariant === "error" ? "Error" : "Info"}
          </ToastTitle>
          <ToastDescription>
            {toastVariant === "success"
              ? "Action completed successfully."
              : toastVariant === "error"
              ? "Something went wrong. Please retry."
              : "Heads up — configuration saved."}
          </ToastDescription>
        </div>
        <ToastClose />
      </Toast>
      <ToastViewport />
    </ToastProvider>
  );
}
