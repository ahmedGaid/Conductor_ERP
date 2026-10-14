import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavIcon } from "../../app/icons";
import { HashLink } from "./HashLink";
import { BrandMark } from "./BrandMark";
import { useReveal } from "./useReveal";
import { useInView } from "./useInView";

/* Shared shapes for the structured i18n content. */
type Module = { id: string; name: string; desc: string; points: string[] };
type KV = { k: string; v: string };
type Impact = { label: string; value: string; dir: "up" | "down" | "flat" };
type Line = { item: string; qty: string };

const ICON_FOR: Record<string, string> = {
  Sales: "sales",
  Inventory: "inventory",
  Purchasing: "purchasing",
  Suppliers: "purchasing",
  Customers: "crm",
  Accounting: "accounting",
  Customer: "crm",
  Supplier: "purchasing",
  accounting: "accounting",
  inventory: "inventory",
  sales: "sales",
  purchasing: "purchasing",
  crm: "crm",
};

/** Section shell: centred title + lede, reveal-on-scroll. No per-section eyebrow (kept to the hero). */
function SectionHead({ title, lede }: { title: string; lede: string }) {
  return (
    <div className="lp-sec__head lp-reveal">
      <h2 className="lp-sec__title">{title}</h2>
      <p className="lp-sec__lede">{lede}</p>
    </div>
  );
}

/**
 * Hub-and-spoke diagram (reused by the Problem and Sync sections). A circle is direction-agnostic,
 * so it reads identically in RTL and LTR. Node positions are computed once; the connective lines are
 * an SVG underlay using the same geometry.
 */
function OrbitDiagram({ hub, nodes }: { hub: string; nodes: string[] }) {
  const R = 40; // radius in % of the box
  const pts = nodes.map((_, i) => {
    const a = (-90 + (i * 360) / nodes.length) * (Math.PI / 180);
    return { x: 50 + R * Math.cos(a), y: 50 + R * Math.sin(a) };
  });
  return (
    <div className="lp-orbit" role="img" aria-label={hub}>
      <svg className="lp-orbit__links" viewBox="0 0 100 100" aria-hidden="true" preserveAspectRatio="none">
        {pts.map((p, i) => (
          <line key={i} x1="50" y1="50" x2={p.x} y2={p.y} />
        ))}
      </svg>
      <div className="lp-orbit__hub">
        <BrandMark className="lp-orbit__hublogo" />
        <span>{hub}</span>
      </div>
      {nodes.map((label, i) => (
        <div
          key={label}
          className="lp-orbit__node"
          /* Physical left/top so the chips share the SVG link geometry; the orbit is a symmetric
             diagram, intentionally identical (not mirrored) in RTL and LTR. */
          style={{ left: `${pts[i].x}%`, top: `${pts[i].y}%` }}
        >
          <span className="lp-orbit__icon" aria-hidden="true">
            <NavIcon name={ICON_FOR[label] ?? "dashboard"} />
          </span>
          {label}
        </div>
      ))}
    </div>
  );
}

export function BusinessProblemSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const nodes = t("landing.story.problem.nodes", { returnObjects: true }) as string[];
  return (
    <section className="lp-sec" id="problem">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.problem.title")} lede={t("landing.story.problem.lede")} />
        <div className="lp-orbit-wrap lp-reveal">
          <OrbitDiagram hub={t("landing.brand")} nodes={nodes} />
        </div>
      </div>
    </section>
  );
}

export function CoreERPSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const modules = t("landing.story.core.modules", { returnObjects: true }) as Module[];
  const [active, setActive] = useState(0);
  const m = modules[active];
  return (
    <section className="lp-sec" id="core">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.core.title")} lede={t("landing.story.core.lede")} />
        <div className="lp-core lp-reveal">
          <div className="lp-core__tabs" role="tablist" aria-label={t("landing.story.core.title")}>
            {modules.map((mod, i) => (
              <button
                key={mod.id}
                role="tab"
                aria-selected={i === active}
                className={`lp-core__tab${i === active ? " is-active" : ""}`}
                onClick={() => setActive(i)}
              >
                <span className="lp-core__tabicon" aria-hidden="true">
                  <NavIcon name={ICON_FOR[mod.id] ?? "dashboard"} />
                </span>
                {mod.name}
              </button>
            ))}
          </div>
          <div className="lp-core__panel" role="tabpanel">
            <div className="lp-core__paneltext">
              <div className="lp-core__panelhead">
                <span className="lp-core__panelicon" aria-hidden="true">
                  <NavIcon name={ICON_FOR[m.id] ?? "dashboard"} />
                </span>
                <div>
                  <h3 className="lp-core__panelname">{m.name}</h3>
                  <p className="lp-core__paneldesc">{m.desc}</p>
                </div>
              </div>
              <ul className="lp-core__points">
                {m.points.map((p) => (
                  <li key={p}>
                    <span className="lp-tick" aria-hidden="true">
                      <NavIcon name="check" />
                    </span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div className="lp-core__shot">
              <img
                key={m.id}
                src={`/landing/shots/${m.id}.png`}
                alt={m.name}
                width={1400}
                height={880}
                loading="lazy"
                decoding="async"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function AIContextSection() {
  const { t } = useTranslation();
  const [ref, inView] = useInView<HTMLDivElement>();
  const chips = t("landing.story.ai.chips", { returnObjects: true }) as string[];
  const sources = t("landing.story.ai.sources", { returnObjects: true }) as string[];
  return (
    <section className="lp-sec" id="ai">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.ai.title")} lede={t("landing.story.ai.lede")} />
        <div className={`lp-ai lp-reveal${inView ? " is-in" : ""}`}>
          <div className="lp-ai__chips">
            {chips.map((c) => (
              <span key={c} className="lp-ai__chip">
                <NavIcon name="sparkle" />
                {c}
              </span>
            ))}
          </div>
          <div className="lp-ai__msg lp-ai__msg--user">
            <p>{t("landing.story.ai.question")}</p>
          </div>
          <div className="lp-ai__msg lp-ai__msg--bot">
            <span className="lp-ai__avatar" aria-hidden="true">
              <NavIcon name="sparkle" />
            </span>
            <div className="lp-ai__bubble">
              <p>{t("landing.story.ai.answer")}</p>
              <div className="lp-ai__sources">
                <span className="lp-ai__srclabel">{t("landing.story.ai.sourceLabel")}</span>
                {sources.map((s) => (
                  <span key={s} className="lp-ai__src">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HumanControlSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const steps = t("landing.story.control.steps", { returnObjects: true }) as string[];
  const lines = t("landing.story.control.lines", { returnObjects: true }) as Line[];
  return (
    <section className="lp-sec" id="control">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.control.title")} lede={t("landing.story.control.lede")} />
        <div className="lp-flow lp-reveal">
          {steps.map((s, i) => (
            <div key={s} className="lp-flow__step">
              <span className="lp-flow__dot">{i + 1}</span>
              {s}
            </div>
          ))}
        </div>
        <div className="lp-propose lp-reveal">
          <div className="lp-propose__prompt">
            <NavIcon name="sparkle" />
            <span>{t("landing.story.control.prompt")}</span>
          </div>
          <div className="lp-propose__card">
            <div className="lp-propose__cardhead">
              <span className="lp-propose__badge">{t("landing.story.control.proposalLabel")}</span>
              <span className="lp-propose__supplier">{t("landing.story.control.supplier")}</span>
            </div>
            <ul className="lp-propose__lines">
              {lines.map((l) => (
                <li key={l.item}>
                  <span>{l.item}</span>
                  <span className="num">{l.qty}</span>
                </li>
              ))}
            </ul>
            <div className="lp-propose__foot">
              <span className="lp-propose__note">
                <NavIcon name="info" />
                {t("landing.story.control.note")}
              </span>
              <div className="lp-propose__actions">
                <span className="lp-btn lp-btn--ghost lp-btn--sm">
                  {t("landing.story.control.review")}
                </span>
                <span className="lp-btn lp-btn--solid lp-btn--sm">
                  {t("landing.story.control.confirm")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SimulationSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const impacts = t("landing.story.simulate.impacts", { returnObjects: true }) as Impact[];
  return (
    <section className="lp-sec" id="simulate">
      <div className="lp-wrap" ref={ref}>
        <SectionHead
          title={t("landing.story.simulate.title")}
          lede={t("landing.story.simulate.lede")}
        />
        <div className="lp-sim lp-reveal">
          <div className="lp-sim__action">
            <NavIcon name="warning" />
            <span>{t("landing.story.simulate.action")}</span>
          </div>
          <div className="lp-sim__grid">
            <span className="lp-sim__col lp-sim__col--now">{t("landing.story.simulate.nowLabel")}</span>
            <span className="lp-sim__col lp-sim__col--after">
              {t("landing.story.simulate.afterLabel")}
            </span>
            {impacts.map((im) => (
              <div key={im.label} className="lp-sim__row">
                <span className="lp-sim__label">{im.label}</span>
                <span className={`lp-sim__delta is-${im.dir}`}>
                  {im.dir !== "flat" && <NavIcon name={im.dir === "up" ? "trendUp" : "trendDown"} />}
                  <span className="num">{im.value}</span>
                </span>
              </div>
            ))}
          </div>
          <p className="lp-sim__note">
            <NavIcon name="checkCircle" />
            {t("landing.story.simulate.note")}
          </p>
        </div>
      </div>
    </section>
  );
}

export function SmartImportSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const steps = t("landing.story.import.steps", { returnObjects: true }) as string[];
  const cols = t("landing.story.import.cols", { returnObjects: true }) as string[];
  const rows = t("landing.story.import.rows", { returnObjects: true }) as string[][];
  return (
    <section className="lp-sec" id="import">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.import.title")} lede={t("landing.story.import.lede")} />
        <div className="lp-import lp-reveal">
          <div className="lp-import__flow">
            <span className="lp-import__file">
              <NavIcon name="paperclip" />
              <span className="num">{t("landing.story.import.file")}</span>
            </span>
            <div className="lp-import__steps">
              {steps.map((s, i) => (
                <span key={s} className="lp-import__step">
                  {s}
                  {i < steps.length - 1 && <span className="lp-import__arrow" aria-hidden="true">›</span>}
                </span>
              ))}
            </div>
          </div>
          <div className="lp-import__preview">
            <div className="lp-import__previewhead">
              <span>{t("landing.story.import.understood")}</span>
              <span className="lp-import__dup">
                <NavIcon name="warning" />
                {t("landing.story.import.dupNote")}
              </span>
            </div>
            <div className="lp-import__table">
              <div className="lp-import__thead">
                {cols.map((c) => (
                  <span key={c}>{c}</span>
                ))}
              </div>
              {rows.map((r, i) => (
                <div key={i} className="lp-import__row">
                  <span>{r[0]}</span>
                  <span className="num">{r[1]}</span>
                  <span className="num">{r[2]}</span>
                </div>
              ))}
            </div>
            <div className="lp-import__foot">
              <span className="lp-btn lp-btn--solid lp-btn--sm">
                <NavIcon name="check" />
                {t("landing.story.import.approve")}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function EgyptSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const points = t("landing.story.egypt.points", { returnObjects: true }) as KV[];
  return (
    <section className="lp-sec" id="egypt">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.egypt.title")} lede={t("landing.story.egypt.lede")} />
        <div className="lp-egypt lp-reveal">
          <ul className="lp-egypt__points">
            {points.map((p) => (
              <li key={p.k}>
                <span className="lp-tick" aria-hidden="true">
                  <NavIcon name="check" />
                </span>
                <div>
                  <span className="lp-egypt__k">{p.k}</span>
                  <span className="lp-egypt__v">{p.v}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="lp-doc" aria-hidden="true">
            <div className="lp-doc__head">
              <span className="lp-doc__title">{t("landing.story.egypt.docTitle")}</span>
              <span className="lp-doc__eta">
                <NavIcon name="einvoice" />
                {t("landing.story.egypt.docNote")}
              </span>
            </div>
            <div className="lp-doc__lines">
              <span className="lp-doc__line" />
              <span className="lp-doc__line" />
              <span className="lp-doc__line lp-doc__line--short" />
            </div>
            <div className="lp-doc__total">
              <span>{t("landing.story.egypt.docTotal")}</span>
              <span className="num">{t("landing.story.egypt.docAmount")}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SecuritySection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const points = t("landing.story.security.points", { returnObjects: true }) as KV[];
  const icons = ["settings", "inventory", "knowledge", "checkCircle", "clock", "sparkle"];
  return (
    <section className="lp-sec" id="security">
      <div className="lp-wrap" ref={ref}>
        <SectionHead
          title={t("landing.story.security.title")}
          lede={t("landing.story.security.lede")}
        />
        <div className="lp-sec-grid lp-reveal">
          {points.map((p, i) => (
            <div key={p.k} className="lp-sec-card">
              <span className="lp-sec-card__icon" aria-hidden="true">
                <NavIcon name={icons[i] ?? "check"} />
              </span>
              <span className="lp-sec-card__k">{p.k}</span>
              <span className="lp-sec-card__v">{p.v}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function BusinessSyncSection() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  const nodes = t("landing.story.sync.nodes", { returnObjects: true }) as string[];
  return (
    <section className="lp-sec" id="sync">
      <div className="lp-wrap" ref={ref}>
        <SectionHead title={t("landing.story.sync.title")} lede={t("landing.story.sync.lede")} />
        <div className="lp-orbit-wrap lp-reveal">
          <OrbitDiagram hub={t("landing.story.sync.hub")} nodes={nodes} />
        </div>
      </div>
    </section>
  );
}

export function FinalCTA() {
  const { t } = useTranslation();
  const ref = useReveal<HTMLDivElement>();
  return (
    <section className="lp-sec lp-final" id="final">
      <div className="lp-wrap lp-reveal" ref={ref}>
        <h2 className="lp-final__title">{t("landing.story.finalCta.title")}</h2>
        <p className="lp-final__sub">{t("landing.story.finalCta.subtitle")}</p>
        <div className="lp-final__cta">
          <a href="#/login" className="lp-btn lp-btn--solid lp-btn--lg lp-btn--shine">
            {t("landing.hero.tryCta")}
          </a>
          <HashLink to="#pricing" className="lp-btn lp-btn--ghost lp-btn--lg">
            {t("landing.hero.secondaryCta")}
          </HashLink>
        </div>
      </div>
    </section>
  );
}
