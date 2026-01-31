import React from "react";

export function Separator({ className = "", orientation = "horizontal", ...props }) {
  const isVertical = orientation === "vertical";
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={[
        "bg-border",
        isVertical ? "w-px h-full" : "h-px w-full",
        className,
      ].join(" ")}
      {...props}
    />
  );
}

export default Separator;
