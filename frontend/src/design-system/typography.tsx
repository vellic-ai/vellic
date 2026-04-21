import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const textVariants = cva("", {
  variants: {
    variant: {
      h1:      "text-[22px] font-semibold tracking-[-0.01em] text-text leading-tight",
      h2:      "text-lg font-semibold text-text leading-snug",
      h3:      "text-base font-semibold text-text leading-snug",
      h4:      "text-sm font-semibold text-text leading-snug",
      body:    "text-base text-text leading-relaxed",
      small:   "text-sm text-text leading-relaxed",
      xs:      "text-xs text-text-muted leading-normal",
      muted:   "text-sm text-text-muted leading-relaxed",
      label:   "text-sm font-medium text-text-muted",
      caption: "text-xs text-text-muted uppercase tracking-[0.06em] font-medium",
      mono:    "font-mono text-sm text-text",
      code:    "font-mono text-xs bg-surface-2 border border-border px-1.5 py-0.5 rounded text-text",
    },
  },
  defaultVariants: { variant: "body" },
});

type VariantKey = NonNullable<VariantProps<typeof textVariants>["variant"]>;

const defaultTags: Record<VariantKey, React.ElementType> = {
  h1: "h1",
  h2: "h2",
  h3: "h3",
  h4: "h4",
  body: "p",
  small: "p",
  xs: "p",
  muted: "p",
  label: "label",
  caption: "span",
  mono: "span",
  code: "code",
};

export interface TextProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof textVariants> {
  as?: React.ElementType;
}

const Text = React.forwardRef<HTMLElement, TextProps>(
  ({ className, variant = "body", as, ...props }, ref) => {
    const Tag = as ?? defaultTags[variant as VariantKey] ?? "p";
    return (
      <Tag
        ref={ref}
        className={cn(textVariants({ variant }), className)}
        {...props}
      />
    );
  }
);
Text.displayName = "Text";

// eslint-disable-next-line react-refresh/only-export-components
export { Text, textVariants };
