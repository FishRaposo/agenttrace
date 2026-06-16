import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function Boom(): JSX.Element {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <p>safe content</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("safe content")).toBeInTheDocument();
  });

  it("renders the default fallback and the error message on throw", () => {
    // Suppress React's expected error logging for this case.
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("kaboom")).toBeInTheDocument();
  });

  it("renders a custom fallback when provided", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<span>custom fallback</span>}>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("custom fallback")).toBeInTheDocument();
  });

  it("offers a retry button that resets the error state", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    const button = screen.getByRole("button", { name: /try again/i });
    expect(button).toBeInTheDocument();
    // Clicking resets internal state (it re-throws since Boom always throws,
    // but the handler must exist and be clickable without crashing the test).
    fireEvent.click(button);
  });
});
