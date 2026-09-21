import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Control demo-mode state by mocking the api module's subscription.
let mockActive = false;
let mockForced = false;
vi.mock("@/lib/api", () => ({
  subscribeDemoMode: (listener: (active: boolean) => void) => {
    listener(mockActive);
    return () => {};
  },
  isDemoForced: () => mockForced,
}));

import { DemoModeBanner } from "@/components/DemoModeBanner";

describe("DemoModeBanner", () => {
  beforeEach(() => {
    mockActive = false;
    mockForced = false;
  });

  it("renders nothing when demo mode is inactive", () => {
    mockActive = false;
    const { container } = render(<DemoModeBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders forced-demo copy when NEXT_PUBLIC_DEMO_MODE is set", () => {
    mockActive = true;
    mockForced = true;
    render(<DemoModeBanner />);
    const banner = screen.getByTestId("demo-mode-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute("data-demo-forced", "true");
    expect(banner).toHaveTextContent(/deterministic fixtures for portfolio review/i);
    expect(banner).toHaveAttribute("role", "status");
  });

  it("renders shorter outage copy when backend fallback activates demo mode", () => {
    mockActive = true;
    mockForced = false;
    render(<DemoModeBanner />);
    const banner = screen.getByTestId("demo-mode-banner");
    expect(banner).toHaveAttribute("data-demo-forced", "false");
    expect(banner).toHaveTextContent(/backend offline/i);
    expect(banner).toHaveTextContent(/sample data/i);
  });
});
