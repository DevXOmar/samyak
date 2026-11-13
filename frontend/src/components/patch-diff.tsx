"use client";
import { useId } from "react";
import { DiffEditor, loader } from "@monaco-editor/react";
import { editorThemes } from "@/lib/editor-themes";
loader.config({ paths: { vs: "/monaco/vs" } });
export default function PatchDiff({
  original,
  modified,
  theme,
}: {
  original: string;
  modified: string;
  theme: "light" | "dark";
}) {
  const id = useId().replaceAll(":", "");
  return (
    <DiffEditor
      height="100%"
      language="python"
      originalModelPath={`inmemory://samyak-diff/${id}/original.py`}
      modifiedModelPath={`inmemory://samyak-diff/${id}/candidate.py`}
      keepCurrentOriginalModel
      keepCurrentModifiedModel
      onMount={(editor) => {
        const models = editor.getModel();
        editor.onDidDispose(() => {
          queueMicrotask(() => {
            models?.original.dispose();
            models?.modified.dispose();
          });
        });
      }}
      original={original}
      modified={modified}
      theme={`samyak-${theme}`}
      beforeMount={(m) =>
        Object.entries(editorThemes).forEach(([key, value]) =>
          m.editor.defineTheme(key, value),
        )
      }
      options={{
        readOnly: true,
        renderSideBySide: true,
        originalEditable: false,
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 12,
        lineHeight: 22,
        fontFamily: "var(--font-mono), monospace",
        scrollBeyondLastLine: false,
        ariaLabel: "Original and candidate source diff",
      }}
    />
  );
}
