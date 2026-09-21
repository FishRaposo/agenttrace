"use client";

import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { isDemoForced, subscribeDemoMode } from "@/lib/api";

/**
 * Banner shown whenever the dashboard is serving demo fixtures because demo
 * mode is forced on or the AgentTrace backend is unreachable.
 */
export function DemoModeBanner(): JSX.Element | null {
  const [active, setActive] = useState(false);
  const forced = isDemoForced();

  useEffect(() => subscribeDemoMode(setActive), []);

  if (!active) {
    return null;
  }

  const message = forced
    ? "Sample data — deterministic fixtures for portfolio review."
    : "Backend offline — showing sample data. Start the server for live telemetry.";

  return (
    <div
      role="status"
      data-testid="demo-mode-banner"
      data-demo-forced={forced ? "true" : "false"}
      className="flex items-center gap-3 border-b border-amber-300 bg-amber-50 px-6 py-2.5 text-sm text-amber-900 dark:border-amber-700/50 dark:bg-amber-950/30 dark:text-amber-200"
    >
      <Database className="h-4 w-4 shrink-0" />
      <span>
        <span className="font-semibold">Demo mode</span> — {message}
      </span>
    </div>
  );
}
