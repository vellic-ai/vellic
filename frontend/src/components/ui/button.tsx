import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap font-medium transition-colors duration-[120ms] disabled:opacity-45 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]",
  {
    variants: {
      variant: {
        default:
          "bg-surface-2 border border-border text-text hover:brightness-95",
        primary:
          "bg-accent border border-accent text-white hover:bg-accent-hover hover:border-accent-hover",
        danger:
          "bg-transparent border border-danger/35 text-danger hover:bg-danger/8 hover:border-danger",
        ghost:
          "bg-transparent border border-transparent text-text-muted hover:bg-surface-2 hover:text-text",
        outline:
          "bg-transparent border border-border text-text hover:bg-surface-2",
      },
      size: {
        default: "h-8 px-3.5 rounded",
        sm:      "h-[26px] px-2.5 text-sm rounded",
        lg:      "h-[38px] px-[18px] rounded",
        icon:    "h-8 w-8 rounded",
      },
    },
    defaultVariants: {
      variant: "default",
      size:    "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

// eslint-disable-next-line react-refresh/only-export-components
export { Button, buttonVariants };
