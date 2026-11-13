"use client";
import { useEffect, useRef } from "react";
import Editor, { loader, type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { sourceColumn } from "@/lib/utils";
import type { Report } from "@/lib/client";
loader.config({ paths: { vs: "/monaco/vs" } });
export default function CodeEditor({
  value,
  onChange,
  findings,
  line,
}: {
  value: string;
  onChange: (v: string) => void;
  findings: Report["findings"];
  line: number | null;
}) {
  const instance = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monaco = useRef<Parameters<OnMount>[1] | null>(null);
  function mark() {
    const model = instance.current?.getModel();
    if (model && monaco.current)
      monaco.current.editor.setModelMarkers(
        model,
        "samyak",
        findings.map((f) => ({
          startLineNumber: f.span.start_line,
          startColumn: sourceColumn(value, f.span.start_line, f.span.start_col),
          endLineNumber: f.span.end_line,
          endColumn: Math.max(
            sourceColumn(value, f.span.end_line, f.span.end_col),
            f.span.start_line === f.span.end_line
              ? sourceColumn(value, f.span.start_line, f.span.start_col) + 1
              : 1,
          ),
          severity: f.evidence === "FAULT_CONFIRMED" ? 8 : 4,
          message: `${f.rule_id}: ${f.explanation} [${f.evidence}]`,
        })),
      );
  }
  useEffect(mark, [findings, value]);
  useEffect(() => {
    if (line && instance.current) {
      instance.current.revealLineInCenter(line);
      instance.current.setPosition({ lineNumber: line, column: 1 });
      instance.current.focus();
    }
  }, [line]);
  return (
    <Editor
      height="440px"
      language="python"
      theme="vs-dark"
      value={value}
      onChange={(v) => onChange(v || "")}
      onMount={(e, m) => {
        instance.current = e;
        monaco.current = m;
        mark();
      }}
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        lineHeight: 23,
        padding: { top: 16 },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 4,
        ariaLabel: "Python source editor",
        wordWrap: "on",
      }}
      loading={
        <div className="p-6 text-zinc-500">Loading local Python editor…</div>
      }
    />
  );
}
