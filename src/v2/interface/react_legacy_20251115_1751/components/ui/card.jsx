import React from "react";

export function Card({ children, className }) {
  return (
    <div
      className={`rounded-2xl shadow-md bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }) {
  return (
    <div className={`px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className }) {
  return (
    <h2 className={`text-lg font-semibold text-neutral-800 dark:text-neutral-100 ${className}`}>
      {children}
    </h2>
  );
}

export function CardContent({ children, className }) {
  return (
    <div className={`px-4 py-4 ${className}`}>
      {children}
    </div>
  );
}