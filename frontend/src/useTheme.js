import { useEffect, useLayoutEffect, useState } from "react";

const key = "pap.appearance";
const valid = (value) => ["light", "dark", "system"].includes(value);
const read = () => {
  try { const value = localStorage.getItem(key); return valid(value) ? value : "system"; }
  catch { return "system"; }
};

export function useTheme() {
  const [theme, updateTheme] = useState(read);
  const [systemDark, setSystemDark] = useState(() => matchMedia("(prefers-color-scheme: dark)").matches);
  const resolvedTheme = theme === "system" ? (systemDark ? "dark" : "light") : theme;
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    return () => { delete document.documentElement.dataset.theme; };
  }, [resolvedTheme]);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const changed = () => setSystemDark(media.matches);
    const stored = (event) => { if (event.key === key || event.key === null) updateTheme(read()); };
    media.addEventListener("change", changed);
    window.addEventListener("storage", stored);
    return () => {
      media.removeEventListener("change", changed);
      window.removeEventListener("storage", stored);
    };
  }, []);
  const setTheme = (value) => {
    if (!valid(value)) return;
    updateTheme(value);
    try { localStorage.setItem(key, value); } catch { /* Continua disponível nesta sessão. */ }
  };
  return { theme, resolvedTheme, setTheme };
}
