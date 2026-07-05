import { lazy, Suspense } from "react";

import { ListSkeleton } from "./ListSkeleton";

// Route-split: the timeline (+ its only-here audit API call) has no business in every detail
// page's eager bundle, so it loads as its own small chunk on first paint of the page that uses it.
const LazyRecordTimeline = lazy(() =>
  import("./RecordTimeline").then((m) => ({ default: m.RecordTimeline })),
);

export function RecordTimeline(props: { entityType: string; entityId: string }) {
  return (
    <Suspense fallback={<ListSkeleton rows={3} title={false} />}>
      <LazyRecordTimeline {...props} />
    </Suspense>
  );
}
