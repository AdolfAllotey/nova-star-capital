// src/ui/ErrorBoundary.jsx
// Version neutre : ne fait que rendre les children, sans UI spéciale

import React from "react";

export default function ErrorBoundary({ children }) {
  return <>{children}</>;
}
