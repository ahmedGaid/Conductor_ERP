import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavIcon } from "../../app/icons";
import { HashLink } from "./HashLink";
import { useReveal } from "./useReveal";
import {
  ANNUAL_DISCOUNT,
  BUILDER_MODULES,
  TIERS,
  formatEgp,
  type Tier,
} from "./pricingData";

const FAQ_ITEMS = ["how", "trial", "perUser", "change", "yearly"] as const;

/** One configured user in the custom builder: a name + the set of module ids they use. */
interface BuilderUser {
  id: number;
  name: string;
  mods: Set<string>;
}

function TierCard({ tier, onEstimate }: { tier: Tier; onEstimate: () => void }) {
  const { t } = useTranslation();
  const p = (k: string) => t(`landing.pricing.${k}`);
  return (
    <article className={`lp-tier${tier.popular ? " is-popular" : ""}`}>
      {tier.popular && <span className="lp-tier__badge">{p("mostPopular")}</span>}
      <h3 className="lp-tier__name">{p(`tiers.${tier.id}.name`)}</h3>
      <p className="lp-tier__desc">{p(`tiers.${tier.id}.desc`)}</p>
      <div className="lp-tier__price">
        {tier.perUser === null ? (
          <span className="lp-tier__custom">{p("custom")}</span>
        ) : (
          <>
            <span className="lp-tier__big num">{formatEgp(tier.perUser)}</span>
            <span className="lp-tier__unit">{p("perUserUnit")}</span>
          </>
        )}
      </div>
      <p className="lp-tier__mods-label">{p("included")}</p>
      <ul className="lp-tier__mods">
        {tier.moduleKeys.map((k) => (
          <li key={k}>
            <span className="lp-tier__tick" aria-hidden="true">
              <NavIcon name="check" />
            </span>
            {p(k)}
          </li>
        ))}
      </ul>
      <HashLink
        to="#pricing-builder"
        className={`lp-btn lp-tier__cta ${tier.solidCta ? "lp-btn--solid" : "lp-btn--ghost"}`}
      >
        {p(tier.perUser === null ? "tiers.ent.cta" : "tiers.bookDemo")}
      </HashLink>
      {tier.estimate && (
        <button type="button" className="lp-tier__estimate" onClick={onEstimate}>
          {p("estimateLink")}
        </button>
      )}
    </article>
  );
}

function CustomBuilder({ open }: { open: boolean }) {
  const { t } = useTranslation();
  const p = (k: string) => t(`landing.pricing.${k}`);
  const priceOf = useMemo(
    () => Object.fromEntries(BUILDER_MODULES.map((m) => [m.id, m.price])),
    [],
  );

  const [seq, setSeq] = useState(1);
  const [users, setUsers] = useState<BuilderUser[]>(() => [
    { id: 1, name: t("landing.pricing.builder.userN", { n: 1 }), mods: new Set(["gl", "inv"]) },
  ]);

  const userTotal = (u: BuilderUser) =>
    [...u.mods].reduce((s, id) => s + (priceOf[id] ?? 0), 0);
  const planTotal = users.reduce((s, u) => s + userTotal(u), 0);
  const yearly = planTotal * 12 * (1 - ANNUAL_DISCOUNT);
  const savings = planTotal * 12 * ANNUAL_DISCOUNT;

  const toggleMod = (uid: number, mid: string) =>
    setUsers((prev) =>
      prev.map((u) => {
        if (u.id !== uid) return u;
        const mods = new Set(u.mods);
        mods.has(mid) ? mods.delete(mid) : mods.add(mid);
        return { ...u, mods };
      }),
    );
  const rename = (uid: number, name: string) =>
    setUsers((prev) => prev.map((u) => (u.id === uid ? { ...u, name } : u)));
  const removeUser = (uid: number) =>
    setUsers((prev) => prev.filter((u) => u.id !== uid));
  const addUser = () => {
    const id = seq + 1;
    setSeq(id);
    setUsers((prev) => [
      ...prev,
      { id, name: t("landing.pricing.builder.userN", { n: prev.length + 1 }), mods: new Set() },
    ]);
  };

  return (
    <div className={`lp-build${open ? " is-open" : ""}`} id="pricing-builder">
      <div className="lp-sec-head">
        <h3>{p("builder.title")}</h3>
        <p>{p("builder.subtitle")}</p>
      </div>
      <div className="lp-builder">
        <div className="lp-builder__bar">
          <span className="lp-builder__h">{p("builder.configure")}</span>
          <span className="lp-builder__hint">{p("builder.hint")}</span>
        </div>

        {users.map((u) => (
          <div key={u.id} className="lp-user">
            <div className="lp-user__top">
              <input
                className="lp-user__name"
                value={u.name}
                maxLength={40}
                aria-label={p("builder.nameLabel")}
                onChange={(e) => rename(u.id, e.target.value)}
              />
              <span className="lp-user__sub">
                <span className="num">{formatEgp(userTotal(u))}</span> <small>EGP</small>
              </span>
              <button
                type="button"
                className="lp-user__del"
                aria-label={p("builder.remove")}
                onClick={() => removeUser(u.id)}
              >
                <NavIcon name="close" />
              </button>
            </div>
            <div className="lp-user__mods">
              {BUILDER_MODULES.map((m) => {
                const on = u.mods.has(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    className={`lp-chip${on ? " is-on" : ""}`}
                    aria-pressed={on}
                    onClick={() => toggleMod(u.id, m.id)}
                  >
                    <span className="lp-chip__tick" aria-hidden="true">
                      <NavIcon name="check" />
                    </span>
                    {t(`landing.pricing.${m.labelKey}`)}
                    <span className="lp-chip__price num">{m.price}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <button type="button" className="lp-add-user" onClick={addUser}>
          <NavIcon name="plus" /> {p("builder.addUser")}
        </button>

        <div className="lp-total">
          <div className="lp-total__figure">
            <span className="lp-total__label">{p("builder.estMonthly")}</span>
            <span className="lp-total__amt">
              <span className="num">{formatEgp(planTotal)}</span>{" "}
              <span className="lp-total__per">{p("builder.perMo")}</span>
            </span>
            <span className="lp-total__yearly">
              {p("builder.payYearly")} <b className="num">{formatEgp(yearly)}</b>{" "}
              {p("builder.egpSave")} <b className="num">{formatEgp(savings)}</b>{" "}
              {p("builder.egpPlusImpl")}
            </span>
          </div>
          <div className="lp-total__cta">
            <HashLink to="#pricing" className="lp-btn lp-btn--solid lp-btn--lg">
              {p("builder.bookDemo")}
            </HashLink>
            <span className="lp-total__note">{p("builder.scopeNote")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PricingSection() {
  const { t } = useTranslation();
  const p = (k: string) => t(`landing.pricing.${k}`);
  const [buildOpen, setBuildOpen] = useState(false);
  const reveal = useReveal<HTMLDivElement>();

  const openBuilder = () => {
    setBuildOpen(true);
    // Let the panel mount before scrolling to it.
    requestAnimationFrame(() => {
      const el = document.getElementById("pricing-builder");
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    });
  };

  return (
    <section className="lp-pricing" id="pricing">
      <div className="lp-wrap" ref={reveal}>
        <div className="lp-pricing__head lp-reveal">
          <h2 className="lp-pricing__title">{p("title")}</h2>
          <p className="lp-pricing__lede">{p("subtitle")}</p>
          <p className="lp-pricing__hybrid">{p("hybrid")}</p>
        </div>

        <div className="lp-tiers lp-reveal">
          {TIERS.map((tier) => (
            <TierCard key={tier.id} tier={tier} onEstimate={openBuilder} />
          ))}
        </div>

        <CustomBuilder open={buildOpen} />

        <div className="lp-faq lp-reveal">
          <h3 className="lp-faq__title">{p("faq.title")}</h3>
          {FAQ_ITEMS.map((k) => (
            <details key={k} className="lp-faq__item">
              <summary className="lp-faq__q">{p(`faq.${k}.q`)}</summary>
              <p className="lp-faq__a">{p(`faq.${k}.a`)}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
