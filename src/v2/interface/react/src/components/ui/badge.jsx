import React from "react";

function cx(...a) {
  return a.filter(Boolean).join(" ");
}

const variants = {
  default:
    "bg-primary text-primary-foreground hover:bg-primary/90",
  secondary:
    "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  outline:
    "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
  destructive:
    "bg-destructive text-destructive-foreground hover:bg-destructive/90",
};

export function Badge({ className = "", variant = "default", ...props }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
        variants[variant] || variants.default,
        className
      )}
      {...props}
    />
  );
}

export default Badge;
