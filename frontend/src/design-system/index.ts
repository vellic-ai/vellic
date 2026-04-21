// Design system barrel — VEL-88
// All components consume tokens from src/styles/globals.css

export { Button, buttonVariants }          from "@/components/ui/button";
export type { ButtonProps }                from "@/components/ui/button";

export { Input }                           from "@/components/ui/input";
export type { InputProps }                 from "@/components/ui/input";

export { Badge, badgeVariants }            from "@/components/ui/badge";
export type { BadgeProps }                 from "@/components/ui/badge";

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

export {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

export {
  Dialog,
  DialogTrigger,
  DialogPortal,
  DialogClose,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
} from "@/components/ui/toast";

export {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectLabel,
  SelectSeparator,
} from "@/components/ui/select";

export { Text, textVariants }              from "./typography";
export type { TextProps }                  from "./typography";

export { ThemeToggle }                     from "@/components/ui/theme-toggle";
export { useTheme, ThemeProvider }         from "@/lib/theme";

export {
  Shell,
  PageHeader,
  EmptyState,
  Skeleton,
  StatusDot,
} from "@/components/Shell";
