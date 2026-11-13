"use client";
import { useSyncExternalStore } from "react";
import { executionReadyToRerun } from "@/lib/readiness";
export default function HistoricalRerun({
  job,
  historical,
  live,
  offline,
  busy,
  rerun,
}: {
  job: string;
  historical: unknown;
  live: unknown;
  offline: boolean;
  busy: boolean;
  rerun: () => void;
}) {
  const dismissed = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return localStorage.getItem(`samyak-rerun-dismissed:${job}`) === "1";
      } catch {
        return false;
      }
    },
    () => true,
  );
  if (dismissed || !executionReadyToRerun(historical, live, offline))
    return null;
  return (
    <div className="historical-inline">
      <span>Previous analysis ran without execution · </span>
      <button disabled={busy} onClick={rerun}>
        Rerun
      </button>
      <details>
        <summary aria-label="About previous execution">Why?</summary>
        <p>
          This immutable report records an unavailable runner. Execution is
          available now; rerunning creates a new job. Existing evidence remains
          unchanged.
        </p>
      </details>
      <button
        aria-label="Dismiss previous execution notice"
        onClick={() => {
          try {
            localStorage.setItem(`samyak-rerun-dismissed:${job}`, "1");
          } catch {}
          window.dispatchEvent(new Event("samyak-rerun-dismissed"));
        }}
      >
        ×
      </button>
    </div>
  );
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("samyak-rerun-dismissed", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("samyak-rerun-dismissed", callback);
  };
}
