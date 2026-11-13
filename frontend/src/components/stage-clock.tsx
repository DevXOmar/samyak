"use client";
import { useSyncExternalStore } from "react";
import type { PipelineEvent } from "@/lib/client";
let tick = 0;
function idle() {
  return () => {};
}
function subscribe(callback: () => void) {
  tick = Date.now();
  const id = setInterval(() => {
    tick = Date.now();
    callback();
  }, 1000);
  return () => clearInterval(id);
}
export function stageDurations(events: PipelineEvent[]) {
  return events.slice(0, -1).map((e, i) => ({
    stage: e.stage,
    seconds: Math.max(
      0,
      (Date.parse(events[i + 1].timestamp) - Date.parse(e.timestamp)) / 1000,
    ),
  }));
}
export default function StageClock({
  events,
  busy,
}: {
  events: PipelineEvent[];
  busy: boolean;
}) {
  const now = useSyncExternalStore(
    busy ? subscribe : idle,
    () => tick,
    () => 0,
  );
  const last = events.at(-1);
  if (!last) return null;
  const first = events[0];
  const end = busy ? now : Date.parse(last.timestamp);
  return (
    <div className="stage-clock" role="status">
      <span>
        {busy ? `Active: ${last.stage}` : `${last.stage}`} · elapsed{" "}
        {Math.max(0, (end - Date.parse(first.timestamp)) / 1000).toFixed(0)}s
        total (including queue)
        {busy
          ? ` · ${Math.max(0, (end - Date.parse(last.timestamp)) / 1000).toFixed(0)}s in stage`
          : ""}
      </span>
      <details>
        <summary>Completed stage durations</summary>
        {stageDurations(events).map((s, i) => (
          <span key={i}>
            {s.stage}: {s.seconds.toFixed(2)}s ·{" "}
          </span>
        ))}
        <p>
          Derived from persisted event timestamps; total elapsed includes queue
          time. Worker processing timings are recorded separately in the report.
          No simulated progress.
        </p>
      </details>
    </div>
  );
}
