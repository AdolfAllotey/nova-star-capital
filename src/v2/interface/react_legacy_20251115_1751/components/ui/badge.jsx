import React from "react";

export function Badge({ className, children, ...props }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-transparent bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200 ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}