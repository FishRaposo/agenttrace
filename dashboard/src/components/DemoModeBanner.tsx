"use client";

import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { subscribeDemoMode } from "@/lib/api";

/**
 * A dismissible banner shown whenever the dashboard is serving demo fixtures
 * because the AgentTrace backend is unreachable (or demo mode is forced on).
 *
 * This makes the offline fallback visible rather than silent — users see they
 * are looking at sample data, not live telemetry.
 */
export function DemoModeBanner(): JSX.Element | null {
  const [active, setActive] = useState(false);

  useEffect(() => subscribeDemoMode(setActive), []);

  if (!active) {
    return null;
  }

  return (
    <div
      role="status"
      data-testid="demo-mode-banner"
      className="flex items-center gap-3 border-b border-amber-300 bg-amber-50 px-6 py-2.5 text-sm text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/30 dark:text-amber-200"
    >
      <Database className="h-4 w-4 shrink-0" />
      <span>
        <span className="font-semibold">Demo mode</span> — the trace backend is
        offline, so the dashboard is showing sample data. Start the AgentTrace
        server to see live telemetry.
      </span>
    </div>
  );
}
