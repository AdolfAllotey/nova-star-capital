import React from "react";
export default function NSCLogo({ className="" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="g" x1="0" x2="1">
          <stop offset="0%" stopColor="#06b6d4"/><stop offset="100%" stopColor="#22c55e"/>
        </linearGradient>
      </defs>
      <path fill="url(#g)" d="M12 2l2.8 5.7L21 9l-4.5 4.4L17.6 21 12 17.8 6.4 21l1-7.6L3 9l6.2-1.3z"/>
    </svg>
  );
}
