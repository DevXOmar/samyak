"use client";
import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/client";
import { Button } from "./ui/button";
import type { components } from "@/lib/api";
export type ImportedFile = components["schemas"]["FileResult"];
type Repository = components["schemas"]["RepoResult"];
export default function GithubImport({
  onOpen,
  onClose,
  dirty,
}: {
  onOpen: (file: ImportedFile) => void;
  onClose: () => void;
  dirty: boolean;
}) {
  const root = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") close.current();
      if (event.key !== "Tab") return;
      const items = Array.from(
        root.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled)",
        ) || [],
      );
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      previous?.focus();
    };
  }, []);
  const [url, setUrl] = useState("");
  const [repo, setRepo] = useState<Repository | null>(null);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [replace, setReplace] = useState(false);
  return (
    <div className="github-dialog-backdrop">
      <section
        ref={root}
        role="dialog"
        aria-modal="true"
        aria-label="Import from GitHub"
        className="panel panel-body github-dialog"
      >
        <h2>Import from GitHub</h2>
        <p className="intro-copy">
          One public Python file, pinned to a commit. Import never executes
          code.
        </p>
        <label>
          Public repository URL
          <input
            autoFocus
            aria-label="Public repository URL"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setRepo(null);
              setPath("");
            }}
            placeholder="https://github.com/OWNER/REPO"
          />
        </label>
        <div className="flex-row mt-3">
          <Button
            disabled={busy || !url}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                const result = await api<Repository>("/v1/github/inspect", {
                  url,
                });
                setRepo(result);
                setPath(result.files[0]?.path || "");
              } catch (e) {
                setError(String(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Inspecting…" : "Inspect repository"}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        {error ? (
          <p role="alert" className="notice error">
            {error}
          </p>
        ) : null}
        {repo ? (
          <>
            <p className="mt-3 mono">
              {repo.repository} · {repo.sha.slice(0, 10)}
            </p>
            <p className="intro-copy">
              {repo.partial ? "Partial repository inspection. " : ""}
              {repo.limits}
            </p>
            <div className="github-files">
              {repo.files.length ? (
                repo.files.map((f) => (
                  <label key={f.path}>
                    <input
                      type="radio"
                      name="github-path"
                      checked={path === f.path}
                      onChange={() => setPath(f.path)}
                    />
                    <span>
                      <strong>{f.path}</strong>
                      <small>
                        {f.functions == null
                          ? "Not inspected"
                          : `${f.functions} functions`}{" "}
                        · {f.size} bytes · {f.reason}
                      </small>
                      {f.caveats.map((c) => (
                        <small key={c}>{c}</small>
                      ))}
                    </span>
                  </label>
                ))
              ) : (
                <p>
                  No eligible Python files found within the inspection limits.
                </p>
              )}
            </div>
            {dirty ? (
              <label className="flex-row">
                <input
                  type="checkbox"
                  checked={replace}
                  onChange={(e) => setReplace(e.target.checked)}
                />
                Replace current source and clear its tests, stdin and evidence
              </label>
            ) : null}
            <Button
              disabled={busy || !path || (dirty && !replace)}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const file = await api<ImportedFile>("/v1/github/file", {
                    url: repo.url,
                    sha: repo.sha,
                    path,
                  });
                  onOpen(file);
                  onClose();
                } catch (e) {
                  setError(String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Open in editor
            </Button>
          </>
        ) : null}
      </section>
    </div>
  );
}
