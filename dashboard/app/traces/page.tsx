"use client";

import { useEffect, useState } from "react";

interface Trace {
  trace_id: string;
  span_id: string;
  name: string;
  duration_ms: number | null;
  tags: Record<string, any>;
}

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/traces")
      .then((r) => r.json())
      .then((data) => {
        setTraces(data.traces || []);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading traces...</p>;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1>Traces</h1>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 8 }}>Trace ID</th>
            <th style={{ textAlign: "left", padding: 8 }}>Name</th>
            <th style={{ textAlign: "left", padding: 8 }}>Duration (ms)</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.span_id} style={{ borderBottom: "1px solid #ddd" }}>
              <td style={{ padding: 8 }}>{t.trace_id.slice(0, 8)}</td>
              <td style={{ padding: 8 }}>{t.name}</td>
              <td style={{ padding: 8 }}>{t.duration_ms?.toFixed(2) || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
