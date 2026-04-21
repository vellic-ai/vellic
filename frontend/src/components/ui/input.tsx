import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "w-full h-[34px] px-3 rounded border bg-input-bg border-border text-text",
        "transition-[border-color,box-shadow] duration-[120ms]",
        "placeholder:text-text-muted/70",
        "focus:border-accent focus:shadow-[var(--focus-ring)]",
        "disabled:opacity-45 disabled:cursor-not-allowed",
        error && "border-error",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";

export { Input };
