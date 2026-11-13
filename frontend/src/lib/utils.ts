import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Python AST columns are UTF-8 byte offsets; Monaco columns count UTF-16 code units. */
export function sourceColumn(source: string, line: number, byteOffset: number) {
  const text = source.split("\n")[line - 1] || "";
  return (
    new TextDecoder().decode(
      new TextEncoder().encode(text).slice(0, byteOffset),
    ).length + 1
  );
}
