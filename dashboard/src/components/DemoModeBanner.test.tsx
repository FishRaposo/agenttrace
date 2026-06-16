import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Control demo-mode state by mocking the api module's subscription.
let mockActive = false;
vi.mock("@/lib/api", () => ({
  subscribeDemoMode: (listener: (active: boolean) => void) => {
    listener(mockActive);
    return () => {};
  },
}));

import { DemoModeBanner } from "@/components/DemoModeBanner";

describe("DemoModeBanner", () => {
  beforeEach(() => {
    mockActive = false;
  });

  it("renders nothing when demo mode is inactive", () => {
    mockActive = false;
    const { container } = render(<DemoModeBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a visible banner when demo mode is active", () => {
    mockActive = true;
    render(<DemoModeBanner />);
    const banner = screen.getByTestId("demo-mode-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/demo mode/i);
    expect(banner).toHaveAttribute("role", "status");
  });
});
