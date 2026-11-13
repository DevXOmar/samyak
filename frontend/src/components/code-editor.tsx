"use client";
import { useCallback, useEffect, useRef } from "react";
import Editor, { loader, type OnMount } from "@monaco-editor/react";
import type { editor, IDisposable } from "monaco-editor";
import { sourceColumn } from "@/lib/utils";
import { editorThemes } from "@/lib/editor-themes";
import type { Report } from "@/lib/client";
loader.config({ paths: { vs: "/monaco/vs" } });
export default function CodeEditor({
  value,
  onChange,
  findings,
  line,
  theme = "light",
  height = "100%",
  onAnalyze,
  onRun,
  onSelect,
  readOnly = false,
  modelPath = "submission.py",
  revealToken = 0,
}: {
  value: string;
  onChange: (v: string) => void;
  findings: Report["findings"];
  line: number | null;
  theme?: "light" | "dark";
  height?: string;
  onAnalyze?: () => void;
  onRun?: () => void;
  onSelect?: (line: number) => void;
  readOnly?: boolean;
  modelPath?: string;
  revealToken?: number;
}) {
  const instance = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monaco = useRef<Parameters<OnMount>[1] | null>(null);
  const lastRevealed = useRef<string>("");
  const decorations = useRef<editor.IEditorDecorationsCollection | null>(null);
  const disposables = useRef<IDisposable[]>([]);
  const handlers = useRef({ onAnalyze, onRun, onSelect });
  useEffect(() => {
    handlers.current = { onAnalyze, onRun, onSelect };
  }, [onAnalyze, onRun, onSelect]);
  const mark = useCallback(() => {
    const model = instance.current?.getModel();
    const m = monaco.current;
    if (!model || !m) return;
    m.editor.setModelMarkers(
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
        severity: [
          "FAULT_CONFIRMED",
          "OBSERVED_RUNTIME_FAULT",
          "SYNTAX_ERROR",
        ].includes(f.evidence)
          ? 8
          : 4,
        message: `${f.rule_id}\n${f.explanation}\n${f.evidence} · ${f.qualification}`,
      })),
    );
    decorations.current?.set(
      findings.map((f) => ({
        range: new m.Range(f.span.start_line, 1, f.span.start_line, 1),
        options: {
          isWholeLine: true,
          glyphMarginClassName: `heat-${f.severity.toLowerCase()}`,
          linesDecorationsClassName: `heat-line-${f.severity.toLowerCase()}`,
          hoverMessage: { value: `${f.severity} · ${f.explanation}` },
        },
      })),
    );
    if (line && lastRevealed.current !== `${line}:${revealToken}`) {
      lastRevealed.current = `${line}:${revealToken}`;
      const finding = findings.find((f) => f.span.start_line === line);
      const selected = finding?.span;
      instance.current?.revealLineInCenter(line);
      instance.current?.setSelection(
        new m.Range(
          line,
          selected ? sourceColumn(value, line, selected.start_col) : 1,
          selected?.end_line || line,
          selected
            ? sourceColumn(value, selected.end_line, selected.end_col)
            : model.getLineMaxColumn(line),
        ),
      );
    }
  }, [findings, line, value, revealToken]);
  useEffect(mark, [mark]);
  useEffect(() => {
    monaco.current?.editor.setTheme(`samyak-${theme}`);
  }, [theme]);
  useEffect(() => () => disposables.current.forEach((d) => d.dispose()), []);
  return (
    <Editor
      height={height}
      keepCurrentModel
      language="python"
      path={modelPath}
      theme={`samyak-${theme}`}
      value={value}
      onChange={(v) => onChange(v || "")}
      beforeMount={(m) =>
        Object.entries(editorThemes).forEach(([name, data]) =>
          m.editor.defineTheme(name, data),
        )
      }
      onMount={(e, m) => {
        instance.current = e;
        monaco.current = m;
        decorations.current = e.createDecorationsCollection();
        mark();
        e.addAction({
          id: "samyak.analyze",
          label: "SAMYAK: Analyze source",
          keybindings: [m.KeyMod.CtrlCmd | m.KeyMod.Shift | m.KeyCode.Enter],
          run: () => handlers.current.onAnalyze?.(),
        });
        e.addAction({
          id: "samyak.run",
          label: "SAMYAK: Run Python script",
          keybindings: [m.KeyMod.CtrlCmd | m.KeyCode.Enter],
          run: () => handlers.current.onRun?.(),
        });
        disposables.current.push(
          e.onMouseDown((event) => {
            if (event.target.position)
              handlers.current.onSelect?.(event.target.position.lineNumber);
          }),
        );
      }}
      options={{
        accessibilitySupport: "auto",
        readOnly,
        minimap: { enabled: !readOnly, maxColumn: 80, renderCharacters: false },
        glyphMargin: true,
        folding: true,
        showFoldingControls: "mouseover",
        fontFamily: "var(--font-mono), monospace",
        fontSize: 13,
        lineHeight: 23,
        padding: { top: 20, bottom: 20 },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 4,
        ariaLabel: "Python source editor",
        wordWrap: "off",
        smoothScrolling: false,
        renderLineHighlight: "line",
        bracketPairColorization: { enabled: true },
      }}
      loading={
        <div className="editor-loading">Loading the local Python editor…</div>
      }
    />
  );
}
