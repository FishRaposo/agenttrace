import { RunDetailView } from "@/components/PortfolioViews";
import { sampleCohort, scenarios } from "@/lib/demo-scenarios";

// The view reads its id through useParams(), so the page stays a server component and
// can export generateStaticParams — re-exporting the client component instead made Next
// treat the module as client and report the params function missing.

// A static export needs every run id at build time. The cohort is generated from the same
// pattern the demo renders from: two scenarios, twenty requests each.
export const dynamicParams = false;

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
