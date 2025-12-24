import React from "react";

export function Table({ className = "", ...props }) {
  return <table className={`w-full border-collapse text-sm ${className}`} {...props} />;
}
export function Thead({ className = "", ...props }) {
  return <thead className={`bg-gray-50 text-gray-700 ${className}`} {...props} />;
}
export function Tbody({ className = "", ...props }) {
  return <tbody className={className} {...props} />;
}
export function Tr({ className = "", ...props }) {
  return <tr className={`border-b last:border-0 ${className}`} {...props} />;
}
export function Th({ className = "", ...props }) {
  return <th className={`px-3 py-2 text-left font-medium ${className}`} {...props} />;
}
export function Td({ className = "", ...props }) {
  return <td className={`px-3 py-2 align-middle ${className}`} {...props} />;
}