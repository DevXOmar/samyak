"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type Job,
  type PipelineEvent,
  type Report,
  type AnalysisRequest,
  type TestCase,
} from "@/lib/client";
export function useAnalysis() {
  const [source, setSourceState] = useState("");
  const [tests, setTestsState] = useState<TestCase[]>([]);
  const [contractDirty, setContractDirty] = useState(false);
  const testsVersion = useRef(0);
  const submittedVersion = useRef(0);
  const setTests = useCallback((value: TestCase[]) => {
    testsVersion.current++;
    setTestsState(value);
    setContractDirty(true);
  }, []);
  const [fixture, setFixture] = useState<AnalysisRequest["fixture"]>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState("idle");
  const stream = useRef<EventSource | null>(null);
  const active = useRef<string | null>(null);
  const lastEvent = useRef(0);
  const sourceRef = useRef("");
  const setSource = useCallback((text: string) => {
    sourceRef.current = text;
    setSourceState(text);
  }, []);
  const finish = useCallback(async (id: string) => {
    try {
      const current = await api<Job>(`/v1/analyses/${id}`);
      if (active.current !== id) return;
      setJob(current);
      if (current.status === "FAILED")
        throw new Error(current.error || "Worker failed");
      const [result, timeline] = await Promise.all([
        api<Report>(`/v1/analyses/${id}/report`),
        api<PipelineEvent[]>(`/v1/analyses/${id}/timeline`),
      ]);
      if (active.current !== id) return;
      setReport(result);
      setEvents(timeline);
      if (testsVersion.current === submittedVersion.current)
        setContractDirty(false);
      setError("");
      setConnection("complete");
    } catch (e) {
      if (active.current === id) {
        setError(String(e));
        setConnection("error");
      }
    } finally {
      if (active.current === id) setBusy(false);
    }
  }, []);
  const watch = useCallback(
    async (next: Job, resume = false) => {
      stream.current?.close();
      active.current = next.id;
      setJob(next);
      setBusy(true);
      setError("");
      if (!resume) {
        setEvents([]);
        lastEvent.current = 0;
      }
      localStorage.setItem("samyak-job-v1", next.id);
      if (["COMPLETED", "FAILED"].includes(next.status)) {
        await finish(next.id);
        return;
      }
      setConnection("connecting");
      const sse = new EventSource(
        `/api/v1/analyses/${next.id}/events?after=${lastEvent.current}`,
      );
      stream.current = sse;
      sse.onopen = () => {
        if (active.current === next.id) {
          setConnection("live");
          setError("");
        }
      };
      sse.addEventListener("stage", (e) => {
        if (active.current !== next.id) return;
        const ev = JSON.parse((e as MessageEvent).data) as PipelineEvent;
        if (ev.id <= lastEvent.current) return;
        lastEvent.current = ev.id;
        setEvents((old) =>
          old.some((v) => v.id === ev.id) ? old : [...old, ev],
        );
        setJob((old) =>
          old
            ? {
                ...old,
                stage: ev.stage,
                updated_at: ev.timestamp,
                status:
                  ev.stage === "completed"
                    ? "COMPLETED"
                    : ev.stage === "failed"
                      ? "FAILED"
                      : ev.stage === "queued"
                        ? "QUEUED"
                        : "RUNNING",
              }
            : old,
        );
      });
      sse.addEventListener("done", () => {
        sse.close();
        void finish(next.id);
      });
      sse.onerror = () => {
        if (active.current === next.id) setConnection("reconnecting");
      };
    },
    [finish],
  );
  useEffect(() => {
    const saved = localStorage.getItem("samyak-job-v1");
    if (saved)
      void api<Job>(`/v1/analyses/${saved}`)
        .then(async (current) => {
          if (active.current) return;
          const request = await api<Report>(
            `/v1/analyses/${saved}/report`,
          ).catch(() => null);
          if (active.current) return;
          if (request) {
            if (!sourceRef.current) setSource(request.source);
            setReport(request);
            setTestsState(request.tests);
          }
          await watch(current);
        })
        .catch(() => localStorage.removeItem("samyak-job-v1"));
    return () => stream.current?.close();
  }, [setSource, watch]);
  const run = useCallback(
    async (
      path = "/v1/analyses",
      body: unknown = { source: sourceRef.current, tests, fixture },
    ) => {
      submittedVersion.current = testsVersion.current;
      setBusy(true);
      setError("");
      try {
        const next = await api<Job>(path, body);
        await watch(next);
      } catch (e) {
        setError(String(e));
        setBusy(false);
        setConnection("error");
      }
    },
    [tests, fixture, watch],
  );
  const load = useCallback(
    async (name: NonNullable<AnalysisRequest["fixture"]>) => {
      try {
        const data = await api<AnalysisRequest>(`/v1/fixtures/${name}`);
        stream.current?.close();
        active.current = null;
        localStorage.removeItem("samyak-job-v1");
        setSource(data.source);
        setTestsState(data.tests || []);
        setContractDirty(false);
        setFixture(name);
        setReport(null);
        setJob(null);
        setEvents([]);
        setError("");
        setConnection("idle");
      } catch (e) {
        setError(String(e));
      }
    },
    [setSource],
  );
  return {
    source,
    setSource,
    tests,
    setTests,
    fixture,
    setFixture,
    job,
    report,
    visibleReport: report?.source === source && !contractDirty ? report : null,
    stale: !!report && (report.source !== source || contractDirty),
    events,
    busy,
    error,
    setError,
    connection,
    run,
    load,
    retry: () => (job && job.status !== "FAILED" ? watch(job, true) : run()),
    restore: () => {
      if (report) {
        setSource(report.source);
        setTestsState(report.tests);
        setContractDirty(false);
      }
    },
  };
}
