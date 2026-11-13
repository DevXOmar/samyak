import type { components } from "./api";
export type Report = components["schemas"]["Report"];
export type Job = components["schemas"]["Job"];
export type TestCase = components["schemas"]["TestCase-Input"];
export type PipelineEvent = components["schemas"]["Event"];
export type AnalysisRequest = components["schemas"]["AnalysisRequest-Input"];
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 400)}`);
  }
  return response.json() as Promise<T>;
}
export function riskLabel(risk: number | null | undefined) {
  return risk == null ? "Unavailable" : `${(risk * 100).toFixed(1)}%`;
}
export function tone(
  verdict: string | null | undefined,
): "good" | "warn" | "bad" | "neutral" {
  if (!verdict) return "neutral";
  if (verdict.startsWith("VALIDATED") || verdict === "PASS") return "good";
  if (verdict.startsWith("REJECTED") || ["FAIL", "ERROR"].includes(verdict))
    return "bad";
  if (["QUEUED", "RUNNING"].includes(verdict)) return "neutral";
  return "warn";
}
export function observed(
  result: Report["original_results"][number] | undefined,
) {
  if (!result) return "Unrun";
  return result.status === "PASS" || result.status === "FAIL"
    ? JSON.stringify(result.output)
    : result.error || result.status;
}

export function observationLabel(
  test: { has_expected?: boolean; property?: unknown; tier?: string },
  result: Report["original_results"][number] | undefined,
) {
  if (!result) return "UNRUN";
  if (result.status === "PASS" && !test.has_expected && !test.property)
    return test.tier === "I" ? "NO_RUNTIME_FAULT" : "RETURNED_NO_ORACLE";
  return result.status;
}
export function observationTone(
  test: { has_expected?: boolean; property?: unknown },
  result: Report["original_results"][number] | undefined,
) {
  return result?.status === "PASS" && !test.has_expected && !test.property
    ? ("neutral" as const)
    : tone(result?.status);
}
