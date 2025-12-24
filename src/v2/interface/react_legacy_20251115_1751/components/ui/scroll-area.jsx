import React from "react";

const ScrollArea = ({ children, className }) => {
  return (
    <div
      className={`overflow-auto rounded-xl max-h-[80vh] pr-2 ${className}`}
      style={{ scrollbarWidth: "thin", scrollbarColor: "#ccc transparent" }}
    >
      {children}
    </div>
  );
};

export { ScrollArea };