import { describe, expect, it } from "vitest";
import { sampleCohort } from "./demo-scenarios";

describe("sample trace timing integrity", () => {
  it.each(["incident", "repaired"] as const)(
    "keeps %s stages sequential and entirely inside their run",
    (scenario) => {
      const { runs, spans } = sampleCohort(scenario);
      for (const run of runs) {
        const stages = spans
          .filter((span) => span.run_id === run.id)
          .sort((a, b) => a.start_time.localeCompare(b.start_time));
        let previousEnd = Date.parse(run.start_time);
        for (const stage of stages) {
          expect(
            Date.parse(stage.start_time),
            `${run.id}/${stage.name} starts before its predecessor ended`,
          ).toBeGreaterThanOrEqual(previousEnd);
          expect(
            Date.parse(stage.end_time!),
            `${run.id}/${stage.name} extends past its recorded run`,
          ).toBeLessThanOrEqual(Date.parse(run.end_time!));
          expect(
            Date.parse(stage.end_time!) - Date.parse(stage.start_time),
          ).toBe(stage.duration_ms);
          previousEnd = Date.parse(stage.end_time!);
        }
      }
    },
  );
});
