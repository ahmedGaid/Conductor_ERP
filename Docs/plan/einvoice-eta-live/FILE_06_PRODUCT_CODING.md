# FILE_06 — Product coding (GPC/EGS/GTIN) for real ETA item identity

> Added 2026-07-22 from a doc dig (`Docs/E invoice/Egyptian_E-Invoice_Guide.md`, GS1 Egypt source).
> Not a blocker for the STOP-gate — surfaces only once real submissions start rejecting on
> `itemCode`. Queue position 8C, after FILE_05.
>
> **DONE 2026-07-22** — EGS path built (founder chose EGS over GS1: free, no purchased-GTIN cost,
> fits SMB onboarding; GS1 stays open as future data-model headroom). `pytest` 245 passed, gate10
> passed, `tsc -b` + i18n parity clean. Uncommitted.

## The gap

`eta_adapter.py` currently sends `itemType: "EGS"` with `itemCode` = the raw internal SKU
([eta_adapter.py](../../../erp/einvoice/services/eta_adapter.py)). That is a placeholder, not a
real EGS code. Per the source doc, a real EGS code is a **composite** ETA must approve before use:

```
Internal SKU + GPC classification + Tax Registration Number (9 digits) + "EGS"
```

Steps per the source: (1) map product → GPC classification, (2) register the composed code on the
e-invoicing portal, (3) submit for ETA review, (4) wait for accept/reject. GS1 support contact:
`einvoice@gs1eg.org` / **16841**. (`itemType: "GS1"` is the alternative path — buy real GTINs from
GS1 Egypt instead of composing EGS codes — decide which path with the founder before building.)

## What's missing in the data model

`ProductItem` (or equivalent) has no field for GPC code, GTIN, EGS code, or its approval state. The
source doc's own recommendation (kept for reference, not gospel): treat internal SKU, GPC, GTIN,
EGS, and "ETA item code" as five distinct fields — SKU is not a legal product identity.

## Scope for this file (draft — refine at build time)

1. Decide GS1 vs EGS path with founder (cost/effort tradeoff — GS1 needs purchased GTINs; EGS is
   free but needs per-product GPC classification + an ETA approval round-trip).
2. Add the chosen code field(s) + an approval-state enum (`pending` / `accepted` / `rejected`) to
   the product model, migration.
3. Settings/product UI to enter and see the code + its state.
4. `eta_adapter.py`: `itemCode` sourced from the real code when accepted; **explicit hard-fail (not
   silent SKU fallback)** if a line's product has no accepted code yet, once live submission is on
   — a rejected/placeholder itemCode on a live document is worse than blocking the invoice.
5. Re-verify the EGS composition + approval flow against current
   `https://sdk.invoicing.eta.gov.eg/` docs and the GS1 Egypt guide at build time — this file's
   detail is second-hand (a re-organized article), not the primary spec artifact FILE_02/03 verified
   against directly.

## Why not now

No product has real GPC/EGS/GTIN data yet, and the STOP-gate (real ETA creds) hasn't opened —
nothing here is testable until both exist. Sequenced after FILE_05 so it doesn't block the
credentials-arrive path; do this once real submissions are actually rejecting on item identity, or
proactively if founder wants to get ahead of it.
