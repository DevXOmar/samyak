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
  const [filename, setFilename] = useState("");
  const [provenance, setProvenance] = useState<Record<string, string> | null>(
    null,
  );
  const [source, setSourceState] = useState("");
  const [stdin, setStdin] = useState("");
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
  const restoreStarted = useRef(false);
  const lastSignal = useRef(0);
  const finishing = useRef<string | null>(null);
  const sourceRef = useRef("");
  const sourceTouched = useRef(false);
  const restoringPending = useRef(false);
  const setSource = useCallback((text: string) => {
    sourceTouched.current = true;
    restoringPending.current = false;
    sourceRef.current = text;
    setSourceState(text);
  }, []);
  const finish = useCallback(
    async (id: string) => {
      if (finishing.current === id) return;
      finishing.current = id;
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
        if (restoringPending.current && !sourceTouched.current)
          setSource(result.source);
        setReport(result);
        window.dispatchEvent(new Event("samyak-analysis-completed"));
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
        if (finishing.current === id) finishing.current = null;
        if (active.current === id) setBusy(false);
      }
    },
    [setSource],
  );
  const watch = useCallback(
    async (next: Job, resume = false) => {
      stream.current?.close();
      active.current = next.id;
      lastSignal.current = Date.now();
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
        lastSignal.current = Date.now();
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
    if (!busy) return;
    let cancelled = false;
    let polling = false;
    const timer = setInterval(async () => {
      const id = active.current;
      if (!id || polling || Date.now() - lastSignal.current < 15000) return;
      polling = true;
      lastSignal.current = Date.now();
      try {
        const current = await api<Job>(`/v1/analyses/${id}`);
        if (cancelled || active.current !== id) return;
        if (["COMPLETED", "FAILED"].includes(current.status)) {
          stream.current?.close();
          await finish(id);
        } else {
          const timeline = await api<PipelineEvent[]>(
            `/v1/analyses/${id}/timeline`,
          );
          if (cancelled || active.current !== id) return;
          setJob((old) =>
            old &&
            old.id === id &&
            Date.parse(old.updated_at) > Date.parse(current.updated_at)
              ? old
              : current,
          );
          setEvents((old) =>
            Array.from(
              new Map([...old, ...timeline].map((e) => [e.id, e])).values(),
            ).sort((a, b) => a.id - b.id),
          );
          lastEvent.current = Math.max(
            lastEvent.current,
            ...timeline.map((e) => e.id),
          );
        }
      } catch {
        if (!cancelled && active.current === id) setConnection("reconnecting");
      } finally {
        polling = false;
      }
    }, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [busy, finish]);
  useEffect(() => {
    if (restoreStarted.current) return () => stream.current?.close();
    restoreStarted.current = true;
    const saved = localStorage.getItem("samyak-job-v1");
    if (saved)
      void api<Job>(`/v1/analyses/${saved}`)
        .then(async (current) => {
          if (active.current) return;
          if (current.status !== "COMPLETED") {
            restoringPending.current = !sourceTouched.current;
            await watch(current);
            return;
          }
          const [request, timeline] = await Promise.all([
            api<Report>(`/v1/analyses/${saved}/report`),
            api<PipelineEvent[]>(`/v1/analyses/${saved}/timeline`),
          ]);
          if (active.current || sourceTouched.current) return;
          if (request) {
            if (!sourceRef.current) setSource(request.source);
            setReport(request);
            const origin = request.intelligence.source_provenance as Record<
              string,
              string
            > | null;
            setProvenance(origin || null);
            setFilename(origin?.path || "");
            setStdin(
              String(
                (
                  request.intelligence.execution as
                    | { stdin?: string }
                    | undefined
                )?.stdin || "",
              ),
            );
            setTestsState(request.tests);
          }
          active.current = current.id;
          setJob(current);
          setEvents(timeline);
          setBusy(false);
          setConnection("complete");
        })
        .catch(() => localStorage.removeItem("samyak-job-v1"));
    return () => stream.current?.close();
  }, [setSource, watch]);
  const run = useCallback(
    async (
      path = "/v1/analyses",
      body: unknown = {
        source: sourceRef.current,
        tests,
        fixture,
        stdin,
        provenance,
      },
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
    [tests, fixture, stdin, provenance, watch],
  );
  const load = useCallback(
    async (name: NonNullable<AnalysisRequest["fixture"]>) => {
      try {
        const data = await api<AnalysisRequest>(`/v1/fixtures/${name}`);
        stream.current?.close();
        active.current = null;
        localStorage.removeItem("samyak-job-v1");
        setFilename("");
        setProvenance(null);
        setSource(data.source);
        setStdin(data.stdin || "");
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
    filename,
    provenance,
    importSource: (
      text: string,
      path: string,
      origin: Record<string, string>,
    ) => {
      stream.current?.close();
      active.current = null;
      localStorage.removeItem("samyak-job-v1");
      setSource(text);
      setFilename(path);
      setProvenance(origin);
      setTestsState([]);
      setStdin("");
      setFixture(null);
      setContractDirty(false);
      setReport(null);
      setJob(null);
      setEvents([]);
      setError("");
      setBusy(false);
      setConnection("idle");
    },
    setSource,
    stdin,
    setStdin,
    tests,
    setTests,
    fixture,
    setFixture,
    job,
    report,
    visibleReport:
      report?.source === source &&
      !contractDirty &&
      String(
        (report.intelligence.execution as { stdin?: string } | undefined)
          ?.stdin || "",
      ) === stdin &&
      (!job || job.id === report.job_id)
        ? report
        : null,
    stale:
      !!report &&
      (report.source !== source ||
        contractDirty ||
        String(
          (report.intelligence.execution as { stdin?: string } | undefined)
            ?.stdin || "",
        ) !== stdin),
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
        setStdin(
          String(
            (report.intelligence.execution as { stdin?: string } | undefined)
              ?.stdin || "",
          ),
        );
        setTestsState(report.tests);
        setContractDirty(false);
      }
    },
  };
}
