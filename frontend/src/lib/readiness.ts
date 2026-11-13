export function executionReadyToRerun(
  historical: unknown,
  live: unknown,
  offline: boolean,
) {
  return (
    !offline && historical === "EXECUTION_UNAVAILABLE" && live === "AVAILABLE"
  );
}
