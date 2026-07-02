/*
 * Inventory action feedback — turns a posted stock movement into an ActionReceipt: what moved, the
 * journal it posted, the numbers, and a deterministic on-hand insight (the resulting balance at the
 * warehouse, and a reorder warning) drawn from the on-hand API after the fact.
 *
 * A failed issue / transfer is almost always insufficient stock, so its error receipt links straight
 * to the receive-stock form prefilled with that item and warehouse — the same clear-the-blocker move
 * the sales delivery path uses.
 *
 * All copy is i18n (feedback.inventory.* / feedback.doc.journal); resolvers stay free of page/DOM.
 */
import type { TFunction } from "i18next";

import type { ActionFeedbackApi, ReceiptFact, ReceiptLink } from "../../app/ActionFeedbackContext";
import { stockOnHand, type Movement, type MovementType } from "../../api/inventory";
import { formatMinor } from "../money";

// The warehouse whose resulting balance is worth reporting: where the goods landed.
function insightWarehouse(mv: Movement): string {
  return mv.type === "transfer" && mv.dest_warehouse_code ? mv.dest_warehouse_code : mv.warehouse_code;
}

function movementFacts(t: TFunction, mv: Movement): ReceiptFact[] {
  const facts: ReceiptFact[] = [
    { label: t("inventory.item.sku"), value: mv.item_sku },
    {
      label: mv.type === "transfer" ? t("inventory.movement.to") : t("inventory.warehouse.code"),
      value: mv.type === "transfer" && mv.dest_warehouse_code ? mv.dest_warehouse_code : mv.warehouse_code,
    },
    { label: t("inventory.onHand.quantity"), value: mv.quantity },
  ];
  if (mv.value_minor > 0) facts.push({ label: t("inventory.onHand.value"), value: formatMinor(mv.value_minor) });
  return facts;
}

/**
 * Show a stock-movement receipt now, then enrich it with the resulting on-hand balance once the
 * lookup lands. Best-effort — a failed insight never disturbs the receipt already on screen.
 */
export function showMovementReceipt(fb: ActionFeedbackApi, t: TFunction, mv: Movement, mode: MovementType): void {
  const documents: ReceiptLink[] = mv.journal_number
    ? [{ label: t("feedback.doc.journal", { no: mv.journal_number }), to: `/go/journal/${encodeURIComponent(mv.journal_number)}` }]
    : [];

  const id = fb.show({
    variant: "success",
    title: t(`feedback.inventory.${mode}.title`, { ref: mv.journal_number || mv.id.slice(0, 8) }),
    context: t(`feedback.inventory.${mode}.context`),
    documents,
    facts: movementFacts(t, mv),
    related: [
      { label: t("feedback.related.item"), to: `/go/item/${encodeURIComponent(mv.item_sku)}` },
      { label: t("feedback.related.onHand"), to: "/inventory" },
    ],
  });

  const wh = insightWarehouse(mv);
  void stockOnHand()
    .then((soh) => {
      const row = soh.rows.find((r) => r.sku === mv.item_sku && r.warehouse_code === wh);
      if (!row) return;
      const insights = [t("feedback.inventory.insight.onHand", { qty: row.quantity, warehouse: wh })];
      const warnings = row.below_reorder ? [t("feedback.inventory.warn.belowReorder", { sku: mv.item_sku })] : undefined;
      fb.update(id, { insights, warnings });
    })
    .catch(() => {});
}

/**
 * Show a failed movement as a rich error receipt. For an issue / transfer (the movements that draw
 * stock down) the receipt links to the receive-stock form prefilled with the same item + warehouse,
 * so the block is one click from being cleared.
 */
export function showMovementError(
  fb: ActionFeedbackApi,
  t: TFunction,
  ctx: { mode: MovementType; itemSku: string; warehouse: string },
  error: unknown,
): void {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const drawsDown = ctx.mode === "issue" || ctx.mode === "transfer";

  fb.show({
    variant: "error",
    title: t(`feedback.inventory.error.${ctx.mode}.title`),
    context: t(`feedback.inventory.error.${ctx.mode}.reason`, { defaultValue: rawMessage }),
    resolutions:
      drawsDown && ctx.itemSku && ctx.warehouse
        ? [
            {
              label: t("feedback.inventory.fix.receive", { sku: ctx.itemSku, warehouse: ctx.warehouse }),
              to: `/inventory/movements?mode=receipt&item=${encodeURIComponent(ctx.itemSku)}&warehouse=${encodeURIComponent(ctx.warehouse)}`,
            },
          ]
        : undefined,
  });
}
