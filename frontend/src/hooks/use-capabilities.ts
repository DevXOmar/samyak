"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client";
import type { components } from "@/lib/api";
export function useCapabilities() {
  const [status, setStatus] = useState<
    components["schemas"]["Capabilities"] | null
  >(null);
  const [offline, setOffline] = useState(false);
  const check = useCallback(
    () =>
      api<components["schemas"]["Capabilities"]>("/v1/capabilities")
        .then((value) => {
          setStatus(value);
          setOffline(false);
        })
        .catch(() => setOffline(true)),
    [],
  );
  useEffect(() => {
    const request =
      api<components["schemas"]["Capabilities"]>("/v1/capabilities");
    let active = true;
    request
      .then((value) => {
        if (active) {
          setStatus(value);
          setOffline(false);
        }
      })
      .catch(() => {
        if (active) setOffline(true);
      });
    window.addEventListener("online", check);
    return () => {
      active = false;
      window.removeEventListener("online", check);
    };
  }, [check]);
  return { status, offline, check };
}
