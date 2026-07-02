# Phase 4 — Sales Order Workspace (the "Linear moment")
# LOW RISK — UI only, over contracts that already enforce correctness.

Honor: Principle 5 (one workspace), 6 (drill + COMPARE), 7–9 (interactive/contextual/
progressive within permission), 10 (consistent skeleton), 4 (timeline visible).

> This phase is the most stack-specific. Code below is a React/TS **reference**.
> If the owner chose APEX/another stack, implement the same *structure and
> contracts*, not this exact JSX. The contracts (Phase 3) are the spec.

## What you will do
1. The fixed document skeleton component (reused by all document modules later).
2. The single dynamic drawer (breadcrumb stack, never multiple drawers).
3. Split/compare view (Principle 6 — core, not later).
4. Contextual action bar rendered from `actions` (server-decided).
5. Draft inline-edit vs Posted lock (driven by server, not client guesses).
6. The traceability timeline panel.
7. Progressive/lazy loading of insight panels.

---

## Step 1 — The skeleton (Principle 10: one skeleton for document transactions)
```tsx
// web/src/workspace/DocumentWorkspace.tsx
export function DocumentWorkspace({ doc }: { doc: SODoc }) {
  return (
    <div className="ws">
      <Breadcrumb path={doc.breadcrumb} />
      <Header party={doc.header.party} status={doc.status} actions={doc.actions} />
      <SmartSummary text={doc.summary} />               {/* "Waiting for delivery" */}
      <WorkflowBar steps={doc.workflow} />               {/* lifecycle, NOT approval */}
      <ApprovalStrip routing={doc.approval} />           {/* separate from lifecycle */}
      <MetricsBar totals={doc.totals} currency={doc.meta.currency} />
      <LineGrid lines={doc.lines} editable={doc.status==='DRAFT'} />
      <Tabs>
        <Tab name="Attachments"/><Tab name="Comments"/>
      </Tabs>
      <Timeline docId={doc.id} lazy />                   {/* Rule 4 surface */}
    </div>
  );
}
```
Note: **WorkflowBar (lifecycle) and ApprovalStrip (human routing) are distinct
components** — do not merge them (your EBS instinct: doc status vs AME).

## Step 2 — Single dynamic drawer (never stack)
```tsx
// web/src/workspace/Drawer.tsx — ONE drawer, breadcrumb push/pop
const [stack, setStack] = useState<DrawerView[]>([]);
function open(v: DrawerView){ setStack(s => [...s, v]); }   // Customer > Invoices > 1032
function back(){ setStack(s => s.slice(0,-1)); }
// Render only stack[stack.length-1]; breadcrumb renders the trail.
// Each drawer view fetches its shaped panel: /so/:id/drawer/customer etc.
```
Forbidden: rendering two drawers at once. If the user needs side-by-side → Step 3.

## Step 3 — Split / Compare (Principle 6 — first-class, not Phase 3)
```tsx
// web/src/workspace/CompareView.tsx
// Triggered by "Compare" action; calls GET /so/compare?ids=...
export function CompareView({ ids }: { ids: number[] }) {
  const cols = useCompare(ids);                 // N shaped headers+totals
  return <div className="grid" style={{gridTemplateColumns:`repeat(${ids.length},1fr)`}}>
    {cols.map(c => <CompareCard key={c.id} doc={c} />)}
  </div>;
}
// Use cases to support on day one: this SO vs customer's last 3; warehouse A vs B stock.
```

## Step 4 — Contextual actions (render server's list ONLY)
```tsx
function ActionBar({ actions }: { actions: string[] }) {
  // actions came from the server (Phase 3). The client NEVER adds 'post'/'reverse'.
  return <>{actions.map(a => <ActionButton key={a} kind={a} />)}</>;
}
```
A clerk simply never receives `post`, so the button cannot appear. Security is in
the payload, not the render (Rule 2).

## Step 5 — Draft vs Posted editing
```tsx
// LineGrid cells: editable only when doc.status==='DRAFT'. On blur -> PATCH /so/:id.
// On POSTED: cells read-only; attempting financial change isn't offered. Metadata
// fields (note, ref, due_date) remain editable IF the server's actions include 'editMeta'.
// Never decide mutability client-side — reflect what the API allows; a rejected
// PATCH (422) shows: "Posted — use Amend or Reverse."
```

## Step 6 — Timeline (Rule 4 made visible)
```tsx
// Renders GET /so/:id/timeline. Each row: time, actor, action, field old→new.
// AI rows render with a badge: source==='ai' shows "suggested by AI · accepted by <user>".
// Reversal pairs render linked (original ↔ reversal) so "why" is answerable.
```

## Step 7 — Performance (progressive, Principle 9)
- **Immediately** render: header, status, workflow, metrics (from the single `/so/:id` call).
- **Lazy** (on view / hover): timeline, customer/item drawer panels, charts, related docs.
- MetricsBar reads pre-computed totals from the document row (Phase 1/2 already
  stored them) — **do not** recompute margin with a fat client-side join. If margin
  is shown, it came pre-computed and permission-shaped from the server.

## The 5-second test (acceptance for this phase)
On opening any SO, within 5 seconds the screen answers:
1. **What's happening?** — status + smart summary + workflow bar.
2. **What can I do next?** — the contextual action bar (server-decided).
3. **Why?** — metrics + one-tap timeline + drawer to customer/item context.

## Verification for Phase 4
```bash
cd web && npm run build && npm run test
# Manual acceptance:
# - Open a DRAFT SO as MANAGER: 'post' button visible; cells editable; edit a price -> autosaves.
# - Post it: cells lock; 'reverse'/'amend' appear; price cells no longer editable.
# - Open same SO as SALES_CLERK: no margin column anywhere; no 'post'/'reverse' buttons.
# - Open drawer Customer > Invoices > one invoice: single drawer, breadcrumb back works.
# - Compare 2 SOs: side-by-side renders (no second drawer).
# - Timeline: shows POST and (after reverse) the linked reversal pair.
```

## What you just built
The workspace users *feel*. Every wow-moment (live entities, one drawer, compare,
contextual actions, inline edit, timeline) sits on top of a server that already
guarantees correctness and permission — so the polish can never betray the books.

## Next file: 06_PHASE5_AI_IN_TRACEABILITY.md
