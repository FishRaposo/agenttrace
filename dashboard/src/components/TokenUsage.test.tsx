import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TokenUsage } from "@/components/TokenUsage";
import { demoSpans } from "@/lib/demoData";

describe("TokenUsage", () => {
  it("shows an empty state when no span carries token usage", () => {
    const noTokens = demoSpans.map((s) => ({ ...s, token_usage: null }));
    render(<TokenUsage spans={noTokens} />);
    expect(screen.getByText("No token data available.")).toBeInTheDocument();
  });

  it("renders a token total when usage is present", () => {
    render(<TokenUsage spans={demoSpans} />);
    expect(screen.getByText("Token Usage")).toBeInTheDocument();
    expect(screen.getByText("Total Tokens")).toBeInTheDocument();
  });
});
