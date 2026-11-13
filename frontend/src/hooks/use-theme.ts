"use client";
import { useSyncExternalStore } from "react";
const subscribe = (notify: () => void) => {
  window.addEventListener("samyak-theme", notify);
  window.addEventListener("storage", notify);
  return () => {
    window.removeEventListener("samyak-theme", notify);
    window.removeEventListener("storage", notify);
  };
};
const snapshot = (): "light" | "dark" =>
  localStorage.getItem("samyak-theme") === "dark" ? "dark" : "light";
export function useTheme() {
  const theme = useSyncExternalStore(
    subscribe,
    snapshot,
    () => "light" as const,
  );
  return [
    theme,
    (next: "light" | "dark") => {
      localStorage.setItem("samyak-theme", next);
      window.dispatchEvent(new Event("samyak-theme"));
    },
  ] as const;
}
