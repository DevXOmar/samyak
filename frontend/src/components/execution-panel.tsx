"use client";
import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { Copy, Eraser } from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { tone, type Report } from "@/lib/client";
import { safeOutput } from "@/lib/execution-output";
import "@xterm/xterm/css/xterm.css";

const TABS = ["Output", "Problems", "Execution Trace"] as const;
export default function ExecutionPanel({
  report,
  busy,
  stale,
  theme,
  stage,
  jobStatus,
  onSelect,
}: {
  report: Report | null;
  busy: boolean;
  stale: boolean;
  theme: "light" | "dark";
  stage?: string;
  jobStatus?: string;
  onSelect: (line: number) => void;
}) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Output");
  const [height, setHeight] = useState(200);
  const [cleared, setCleared] = useState(false);
  const [copied, setCopied] = useState("");
  const host = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const result = report?.script_result;
  const output = cleared
    ? ""
    : safeOutput(
        result
          ? result.stdout +
              (result.stderr ? `\n[stderr]\n${result.stderr}` : "")
          : report?.original_results
              .map((r) => `${r.test_id}: ${r.stdout || r.error || r.status}`)
              .join("\n") || "",
      );
  useEffect(() => {
    if (!host.current) return;
    const term = new Terminal({
      disableStdin: true,
      convertEol: true,
      screenReaderMode: true,
      cursorBlink: false,
      fontSize: 12,
      fontFamily: "Geist Mono, monospace",
      scrollback: 2000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(host.current);
    terminal.current = term;
    const observer = new ResizeObserver(() => {
      if (host.current?.clientWidth && host.current?.clientHeight) fit.fit();
    });
    observer.observe(host.current);
    return () => {
      observer.disconnect();
      terminal.current = null;
      term.dispose();
    };
  }, []);
  useEffect(() => {
    const term = terminal.current;
    if (!term) return;
    term.options.theme =
      theme === "dark"
        ? {
            background: "#15171A",
            foreground: "#ECE9E3",
            selectionBackground: "#CFAC7440",
          }
        : {
            background: "#FFFFFF",
            foreground: "#1F2123",
            selectionBackground: "#B8905A40",
          };
    term.reset();
    if (output) term.write(output);
  }, [output, theme]);
  const languageNote = report?.limitations.find((text) =>
    text.startsWith("Python is the supported language."),
  );
  const message = busy
    ? `Job ${jobStatus || "SUBMITTING"} · ${stage || "submitting"}. Results arrive through persisted worker events; execution is bounded and cancellation is not supported.`
    : stale
      ? "Source or stdin changed. Previous execution output is invalidated."
      : !report
        ? "Run Python to capture actual output. Analyze adds the available structural and repair evidence."
        : report.verdict === "REJECTED_SYNTAX"
          ? "Python source could not be parsed. See Problems for the exact diagnostic."
          : result
            ? result.error ||
              (result.stdout || result.stderr
                ? ""
                : "Execution produced no stdout or stderr.")
            : "Function-test observations are shown below. Run executes the complete module as __main__.";
  return (
    <section className="execution-panel" aria-label="Python execution panel">
      <div className="execution-toolbar">
        <div
          role="tablist"
          aria-label="Execution views"
          onKeyDown={(event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
              return;
            event.preventDefault();
            const index =
              event.key === "Home"
                ? 0
                : event.key === "End"
                  ? 2
                  : (TABS.indexOf(tab) + (event.key === "ArrowRight" ? 1 : 2)) %
                    3;
            setTab(TABS[index]);
            document.getElementById(`execution-tab-${index}`)?.focus();
          }}
        >
          {TABS.map((label, i) => (
            <button
              key={label}
              role="tab"
              id={`execution-tab-${i}`}
              aria-controls={`execution-view-${i}`}
              aria-selected={tab === label}
              tabIndex={tab === label ? 0 : -1}
              onClick={() => setTab(label)}
            >
              {label}
              {label === "Problems" && report?.findings.length
                ? ` (${report.findings.length})`
                : ""}
            </button>
          ))}
        </div>
        <div className="flex-row">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Copy output"
            disabled={!output}
            onClick={() => {
              void navigator.clipboard.writeText(output).then(
                () => setCopied("Copied"),
                () => setCopied("Copy unavailable"),
              );
            }}
          >
            <Copy size={12} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Clear output view"
            disabled={!output}
            onClick={() => setCleared(true)}
          >
            <Eraser size={12} />
          </Button>
        </div>
      </div>
      <div className="execution-resize">
        <label>
          Panel height{" "}
          <input
            type="range"
            aria-label="Execution panel height"
            min={120}
            max={450}
            step={10}
            value={height}
            onChange={(e) => setHeight(Number(e.target.value))}
          />
        </label>
        <span role="status">
          {copied ||
            (result
              ? result.status.replaceAll("_", " ")
              : busy
                ? `${jobStatus || "SUBMITTING"} · ${stage || "submitting"}`
                : "READY")}
        </span>
      </div>
      {languageNote ? (
        <p className="execution-message" role="status">
          {languageNote}
        </p>
      ) : null}
      <div className="execution-views" style={{ height }}>
        <div
          id="execution-view-0"
          role="tabpanel"
          aria-labelledby="execution-tab-0"
          hidden={tab !== "Output"}
        >
          {message ? (
            <p className="execution-message" role="status">
              {message}
            </p>
          ) : null}
          <div ref={host} className="execution-terminal" />
          <pre className="sr-only" data-testid="execution-output-text">
            {output}
          </pre>
        </div>
        <div
          id="execution-view-1"
          role="tabpanel"
          aria-labelledby="execution-tab-1"
          hidden={tab !== "Problems"}
        >
          {report?.findings.length ? (
            report.findings.map((f) => (
              <button
                className="execution-problem"
                key={f.id}
                onClick={() => onSelect(f.span.start_line)}
              >
                <Badge
                  tone={tone(
                    f.evidence === "OBSERVED_RUNTIME_FAULT" ? "ERROR" : null,
                  )}
                >
                  {f.evidence}
                </Badge>
                <code>L{f.span.start_line}</code>
                <span>{f.explanation}</span>
              </button>
            ))
          ) : (
            <p className="execution-message">
              {busy
                ? "Computing diagnostics…"
                : "No current diagnostics. This does not establish correctness."}
            </p>
          )}
        </div>
        <div
          id="execution-view-2"
          role="tabpanel"
          aria-labelledby="execution-tab-2"
          hidden={tab !== "Execution Trace"}
        >
          {result ? (
            <div className="execution-trace">
              <p>
                {result.status} · exit {result.exit_code ?? "unavailable"} ·{" "}
                {result.duration_ms == null
                  ? "duration unavailable"
                  : `${result.duration_ms.toFixed(2)} ms`}{" "}
                · domain unconfirmed
              </p>
              <p>
                Covered executable lines:{" "}
                {result.lines.join(", ") || "unavailable"}
              </p>
              {result.fault_lines.map((at, i) => (
                <button
                  key={`${at}-${i}`}
                  onClick={() => onSelect(at)}
                  className="trace-link"
                >
                  submission.py:{at} — jump to source
                </button>
              ))}
              {result.traceback ? (
                <pre>{result.traceback}</pre>
              ) : (
                <p>{result.error || "No exception traceback recorded."}</p>
              )}
              <p className="muted">
                Executed is distinct from validated. This observation has no
                output oracle. Terminal controls are removed from displayed
                output.
              </p>
            </div>
          ) : (
            <p className="execution-message">
              {busy
                ? "Waiting for isolated execution…"
                : "No script execution trace for the current buffer."}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
