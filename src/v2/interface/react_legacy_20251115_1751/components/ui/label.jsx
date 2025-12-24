import React, { forwardRef } from "react";

function cn(...cls) {
  return cls.filter(Boolean).join(" ");
}

const Label = forwardRef(({ className = "", htmlFor, children, ...props }, ref) => {
  return (
    <label
      ref={ref}
      htmlFor={htmlFor}
      className={cn("block text-sm font-medium text-foreground", className)}
      {...props}
    >
      {children}
    </label>
  );
});

Label.displayName = "Label";

export { Label };
export default Label;