import React, { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(
    typeof window !== "undefined" &&
      (localStorage.getItem("theme") === "dark" ||
       (!localStorage.getItem("theme") &&
        window.matchMedia("(prefers-color-scheme: dark)").matches))
  );

  useEffect(() => {
    const html = document.documentElement;
    if (dark) {
      html.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      html.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [dark]);

  return (
    <button
      onClick={() => setDark(d => !d)}
      className="inline-flex items-center gap-2 rounded-xl border px-3 py-1 text-sm
                 border-slate-300 dark:border-slate-700
                 bg-white dark:bg-slate-900"
      title="Basculer clair/sombre"
    >
      {dark ? <Sun size={16}/> : <Moon size={16}/>}
      <span className="hidden sm:inline">{dark ? "Clair" : "Sombre"}</span>
    </button>
  );
}
