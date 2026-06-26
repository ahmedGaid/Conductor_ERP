import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { getMe, getOrgPreferences } from "../api/identity";
import { getSetupStatus } from "../api/setup";
import { listItems } from "../api/inventory";
import { listCustomers, listOrders } from "../api/sales";
import { useAsync } from "../hooks/useAsync";
import { SYSTEM_ADMIN } from "./settings/roles";

// "What to do next" — the post-setup checklist a fresh org lands on (Growth PR 1.6). Each step
// auto-checks off real progress (data → momentum), so it quietly disappears once the org is up and
// running. Admin-only (only they can act on these), dismissible (a services-only business may never
// add a product, and Conductor doesn't nag), and never shown to an established org.
const DISMISS_KEY = "erp.gettingStartedDismissed";

interface Step {
  key: string;
  to: string;
  done: boolean;
}

// Each module list is fetched defensively (a 403 simply leaves that step unchecked) so the panel
// never breaks the dashboard — mirrors how the "needs attention" panel composes module data.
async function loadOnboarding() {
  const [me, org, setup, customers, items, orders] = await Promise.all([
    getMe(),
    getOrgPreferences().catch(() => null),
    getSetupStatus().catch(() => null),
    listCustomers().catch(() => []),
    listItems().catch(() => []),
    listOrders().catch(() => []),
  ]);
  return { me, org, setup, customers, items, orders };
}

export function GettingStarted() {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISS_KEY) === "1");
  const { data } = useAsync(loadOnboarding, [], "onboarding");

  if (dismissed || !data) return null;
  if (!(data.me.roles?.includes(SYSTEM_ADMIN) ?? false)) return null;

  const steps: Step[] = [
    { key: "profile", to: "/settings/organization", done: !!data.org?.company_name?.trim() },
    { key: "accounts", to: "/accounting", done: !!data.setup?.chart_of_accounts.seeded },
    { key: "customer", to: "/sales/customers", done: data.customers.length > 0 },
    { key: "item", to: "/inventory/items", done: data.items.length > 0 },
    { key: "invoice", to: "/sales/orders/new", done: data.orders.length > 0 },
  ];
  // Up and running — retire the panel for good.
  if (steps.every((s) => s.done)) return null;
  const doneCount = steps.filter((s) => s.done).length;

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  }

  return (
    <div className="card dash__panel dash__start">
      <div className="dash__panel-head">
        <h2>{t("dashboard.gettingStarted.title")}</h2>
        <button className="dash__start-dismiss" type="button" onClick={dismiss}>
          {t("dashboard.gettingStarted.dismiss")}
        </button>
      </div>
      <p className="dash__start-lede">
        {t("dashboard.gettingStarted.progress", { done: doneCount, total: steps.length })}
      </p>
      <ul className="dash__start-list">
        {steps.map((s) => (
          <li key={s.key}>
            <Link
              className={`dash__start-item${s.done ? " dash__start-item--done" : ""}`}
              to={s.to}
            >
              <span className="dash__start-check" aria-hidden="true">
                {s.done ? "✓" : ""}
              </span>
              <span className="dash__start-text">
                {t(`dashboard.gettingStarted.steps.${s.key}`)}
              </span>
              {!s.done && (
                <span className="dash__start-arrow" aria-hidden="true">
                  ›
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
