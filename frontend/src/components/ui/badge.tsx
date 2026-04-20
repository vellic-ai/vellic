import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 h-5 px-2 rounded-full text-xs font-medium border whitespace-nowrap",
  {
    variants: {
      variant: {
        default:
          "bg-surface-2 border-border text-text-muted",
        success:
          "bg-success/8 border-success/30 text-success",
        error:
          "bg-error/8 border-error/30 text-error",
        warning:
          "bg-warning-bg border-warning-border text-warning-text",
        info:
          "bg-accent/10 border-accent/35 text-[#8ea3ff]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
