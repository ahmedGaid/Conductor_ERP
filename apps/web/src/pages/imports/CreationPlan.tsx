import { useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { Bdi } from "../../components/Bdi";
import { entityLabelKey, type ImportCreationPlanEntry } from "../../api/smartImports";

interface Group {
  entity: string;
  entries: ImportCreationPlanEntry[];
}

function groupByEntity(entries: ImportCreationPlanEntry[]): Group[] {
  const byEntity = new Map<string, ImportCreationPlanEntry[]>();
  for (const e of entries) {
    const list = byEntity.get(e.entity) ?? [];
    list.push(e);
    byEntity.set(e.entity, list);
  }
  return [...byEntity.entries()].map(([entity, entries]) => ({ entity, entries }));
}

export function CreationPlan({
  entries,
  approved,
  onToggle,
  onApprove,
  applying,
}: {
  entries: ImportCreationPlanEntry[];
  approved: Set<string>;
  onToggle: (key: string) => void;
  onApprove: () => void;
  applying: boolean;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (entries.length === 0) return null;

  const groups = groupByEntity(entries);
  const actionable = entries.filter((e) => e.action === "create" || e.action === "link");
  const doneCount = entries.filter((e) => e.outcome).length;
  const allDone = actionable.length > 0 && doneCount === actionable.length;

  return (
    <section className="imports-plan card">
      <header className="imports-plan__head">
        <h2 className="imports-plan__title">{t("imports.creationPlan.title")}</h2>
        <p className="imports-plan__hint">{t("imports.creationPlan.hint")}</p>
      </header>

      <ul className="imports-plan__groups">
        {groups.map((g) => {
          const open = expanded.has(g.entity);
          return (
            <li key={g.entity} className="imports-plan__group">
              <button
                type="button"
                className="imports-plan__group-toggle"
                onClick={() =>
                  setExpanded((s) => {
                    const next = new Set(s);
                    if (next.has(g.entity)) next.delete(g.entity);
                    else next.add(g.entity);
                    return next;
                  })
                }
                aria-expanded={open}
              >
                <NavIcon name={open ? "expand" : "plus"} />
                {t("imports.creationPlan.groupCount", {
                  count: g.entries.length,
                  entity: t(entityLabelKey(g.entity), g.entity),
                })}
              </button>

              {open && (
                <ul className="imports-plan__entries">
                  {g.entries.map((e) => {
                    const key = `${e.entity}:${e.value}`;
                    const blocked = e.action === "blocked_unsupported" || e.action === "blocked_permission";
                    return (
                      <li key={key} className="imports-plan__entry">
                        {!blocked && !e.outcome && (
                          <input
                            type="checkbox"
                            checked={approved.has(key)}
                            onChange={() => onToggle(key)}
                            aria-label={e.value}
                          />
                        )}
                        <Bdi>
                          <span className="imports-plan__value">{e.value}</span>
                        </Bdi>
                        {e.action === "link" && !e.outcome && (
                          <span className="imports-plan__tag muted">{t("imports.creationPlan.willLink")}</span>
                        )}
                        {e.action === "create" && !e.outcome && (
                          <span className="imports-plan__tag muted">{t("imports.creationPlan.willCreate")}</span>
                        )}
                        {e.outcome && (
                          <span className="imports-plan__tag imports-plan__tag--done">
                            <NavIcon name="check" />
                            {t(`imports.creationPlan.outcome.${e.outcome}`)}
                          </span>
                        )}
                        {blocked && (
                          <span className="imports-plan__tag imports-plan__tag--blocked">
                            {t(`imports.creationPlan.blocked.${e.action}`)}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      <footer className="imports-plan__foot">
        {allDone ? (
          <span className="imports-plan__done muted">
            <NavIcon name="check" />
            {t("imports.creationPlan.allDone")}
          </span>
        ) : (
          <button
            type="button"
            className="btn btn--primary"
            disabled={applying || approved.size === 0}
            onClick={onApprove}
          >
            {applying ? t("common.loading") : t("imports.creationPlan.approve", { count: approved.size })}
          </button>
        )}
      </footer>
    </section>
  );
}
