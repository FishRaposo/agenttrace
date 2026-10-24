import type { Metadata } from "next";
import { PortfolioShell } from "@/components/PortfolioShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import "./globals.css";
export const metadata: Metadata = {
  title: "AgentTrace — Investigate AI workflow failures",
  description:
    "Inspect concurrent requests, diagnose a failing stage, and compare a measured repair.",
  openGraph: {
    title: "AgentTrace — Investigate AI workflow failures",
    description:
      "Inspect concurrent requests, diagnose a failing stage, and compare a measured repair.",
    siteName: "AgentTrace",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AgentTrace — Investigate AI workflow failures",
    description:
      "Inspect concurrent requests, diagnose a failing stage, and compare a measured repair.",
  },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <PortfolioShell>
          <ErrorBoundary>{children}</ErrorBoundary>
        </PortfolioShell>
      </body>
    </html>
  );
}
