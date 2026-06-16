import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CostBreakdown } from "@/components/CostBreakdown";
import { demoSpans } from "@/lib/demoData";

describe("CostBreakdown", () => {
  it("shows an empty state when there are no spans", () => {
    render(<CostBreakdown spans={[]} />);
    expect(screen.getByText("No cost data available.")).toBeInTheDocument();
  });

  it("renders a per-type cost summary and a total when spans are present", () => {
    render(<CostBreakdown spans={demoSpans} />);
    expect(screen.getByText("Cost Breakdown")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    // demoSpans include LLM and tool/decision span types
    expect(screen.getByText(/LLM Calls/)).toBeInTheDocument();
  });
});
