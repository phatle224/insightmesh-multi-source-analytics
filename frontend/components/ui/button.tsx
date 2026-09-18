import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "default" | "small" | "icon";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-on-accent shadow-sm hover:bg-accent-hover active:bg-accent-hover disabled:bg-muted disabled:text-muted-foreground",
  secondary:
    "border border-primary bg-card text-primary hover:bg-muted active:bg-border disabled:border-border disabled:text-muted-foreground",
  ghost: "text-muted-foreground hover:bg-muted hover:text-text active:bg-border",
};

const sizes: Record<ButtonSize, string> = {
  default: "min-h-11 px-4 py-2.5 text-sm",
  small: "min-h-9 px-3 py-1.5 text-sm",
  icon: "size-11 p-0",
};

export function Button({
  asChild = false,
  className,
  variant = "primary",
  size = "default",
  type = "button",
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        sizes[size],
        className,
      )}
      type={asChild ? undefined : type}
      {...props}
    />
  );
}
