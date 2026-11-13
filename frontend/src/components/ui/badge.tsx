import { cn } from "@/lib/utils";
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex rounded-md border px-2 py-1 text-[10px] font-semibold tracking-wide",
        {
          neutral: "border-zinc-700 bg-zinc-800/60 text-zinc-300",
          good: "border-teal-800 bg-teal-950 text-teal-300",
          warn: "border-amber-900 bg-amber-950/60 text-amber-300",
          bad: "border-rose-900 bg-rose-950/60 text-rose-300",
        }[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
