import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "SAMYAK · Evidence-driven code intelligence",
  description:
    "Predict defects, investigate source, and validate repairs with replayable evidence.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
