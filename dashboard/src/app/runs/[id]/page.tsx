import { RunDetailView } from "@/components/PortfolioViews";

// The view reads its id through useParams(), so the page stays a server component and can export
// generateStaticParams — re-exporting the client component made Next treat the module as client
// and report the params function missing.
//
// dynamicParams stays at its default: route segment config must be a literal, and an export has no
// server to route unknown ids anyway — Pages answers them with 404.html. Keeping the default also
// leaves a connected build free to serve any real run id.

// The sample cohort is generated from the same pattern the demo renders from: two scenarios,
// twenty requests each.
export function generateStaticParams() {
  return ["incident", "repaired"].flatMap((scenario) =>
    Array.from({ length: 20 }, (_, index) => ({
      id: `sample-${scenario}-request-${String(index + 1).padStart(2, "0")}`,
    })),
  );
}

export default function RunDetailPage() {
  return <RunDetailView />;
}
