import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { SegmentedControl } from "../../components/SegmentedControl";

type PricingTab = "lists" | "customers";

/** Sub-nav for the Pricing section: switch between price lists and per-customer pricing. */
export function PricingTabs({ active }: { active: PricingTab }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <SegmentedControl<PricingTab>
      value={active}
      ariaLabel={t("pricing.tabs.aria")}
      options={[
        { value: "lists", label: t("pricing.tabs.lists") },
        { value: "customers", label: t("pricing.tabs.customers") },
      ]}
      onChange={(v) => navigate(v === "lists" ? "/pricing" : "/pricing/customers")}
    />
  );
}
