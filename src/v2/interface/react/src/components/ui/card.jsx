import React from "react";

function cx(...a) {
  return a.filter(Boolean).join(" ");
}

export function Card({ className = "", ...props }) {
  return (
    <div
      className={cx(
        "rounded-xl border bg-background text-foreground shadow-sm",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className = "", ...props }) {
  return (
    <div className={cx("flex flex-col gap-1.5 p-6", className)} {...props} />
  );
}

export function CardTitle({ className = "", ...props }) {
  return (
    <h3
      className={cx("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  );
}

export function CardContent({ className = "", ...props }) {
  return <div className={cx("p-6 pt-0", className)} {...props} />;
}

export default Card;
