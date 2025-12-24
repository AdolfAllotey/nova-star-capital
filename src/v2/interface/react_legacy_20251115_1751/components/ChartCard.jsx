import React from "react";

const ChartCard = ({ title, description, children }) => {
  return (
    <div className="bg-card rounded-2xl shadow-md p-4 sm:p-6">
      <div className="mb-4">
        <h2 className="text-lg sm:text-xl font-semibold">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>
      <div className="h-[300px] sm:h-[350px]">{children}</div>
    </div>
  );
};

export { ChartCard };