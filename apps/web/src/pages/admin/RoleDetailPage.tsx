import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  deleteRole,
  getRole,
  getRoleRegistry,
  setApprovalLimit,
  setRolePermission,
  type RoleDetail,
  type RoleRegistry,
} from "../../api/roles";
import { formatMinor, parseToMinor } from "../../lib/money";
import "./admin.css";

export function RoleDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const name = decodeURIComponent(params.name ?? "");

  const [role, setRole] = useState<RoleDetail | null>(null);
  const [registry, setRegistry] = useState<RoleRegistry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    Promise.all([getRole(name), getRoleRegistry()])
      .then(([r, reg]) => { setRole(r); setRegistry(reg); })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [name]);

  useEffect(load, [load]);

  // Only the System Admin role is read-only (it bypasses every check, so granting it anything is
  // meaningless). Built-in roles ARE editable — an admin tunes their permissions and approval limits
  // here — they just can't be deleted (guarded separately).
  const readOnly = !!role && role.is_admin;

  async function mutate(p: Promise<RoleDetail>) {
    setError(null);
    try {
      setRole(await p);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function onDelete() {
    if (!role || !window.confirm(t("admin.roles.deleteConfirm"))) return;
    try {
      await deleteRole(role.name);
      navigate("/admin/roles");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (error && !role) return <section className="page-enter"><p className="error-text">{error}</p></section>;
  if (!role || !registry) {
    return (
      <section className="page-enter">
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
        </div>
      </section>
    );
  }

  return (
    <section className="page-enter">
      <Link className="admin-back" to="/admin/roles">← {t("admin.roles.back")}</Link>

      <header className="admin-detail__head">
        <div className="admin-detail__id">
          <h1>{role.name}</h1>
          <p className="muted">
            <span className={`upill ${role.protected ? "upill--invited" : "upill--active"}`}>
              {t(role.protected ? "admin.roles.builtin" : "admin.roles.custom")}
            </span>
            {" "}{t("admin.roles.memberCount", { count: role.members })}
          </p>
        </div>
        {!role.protected && (
          <button className="btn btn--danger" onClick={onDelete}>{t("admin.roles.delete")}</button>
        )}
      </header>

      {role.is_admin && <p className="admin-notice">{t("admin.roles.adminNote")}</p>}
      {role.protected && !role.is_admin && <p className="admin-notice">{t("admin.roles.protectedNote")}</p>}
      {error && <p className="error-text">{error}</p>}
      {notice && <p className="admin-notice">{notice}</p>}

      <PermissionMatrix
        role={role}
        registry={registry}
        readOnly={readOnly}
        onToggle={(code, scope, granted) => mutate(setRolePermission(role.name, code, scope, granted))}
      />

      <ApprovalLimits
        role={role}
        registry={registry}
        readOnly={readOnly}
        onSet={(doc, value) => mutate(setApprovalLimit(role.name, doc, value)).then(() => setNotice(t("admin.roles.saved")))}
      />
    </section>
  );
}

function humanize(code: string): string {
  return code.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function PermissionMatrix({
  role,
  registry,
  readOnly,
  onToggle,
}: {
  role: RoleDetail;
  registry: RoleRegistry;
  readOnly: boolean;
  onToggle: (code: string, scope: string, granted: boolean) => void;
}) {
  const { t } = useTranslation();
  // Per-entity scope chosen in the UI: scope applies to that entity's granted actions. Seeded from
  // the scope of any grant already on the entity, defaulting to the broadest ("all").
  const [scopeFor, setScopeFor] = useState<Record<string, string>>({});

  function rowScope(module: string, entity: string): string {
    const key = `${module}.${entity}`;
    if (scopeFor[key]) return scopeFor[key];
    const existing = Object.entries(role.permissions).find(([c]) => c.startsWith(`${key}.`));
    return existing ? existing[1] : "all";
  }

  function changeRowScope(module: string, entity: string, scope: string) {
    const key = `${module}.${entity}`;
    setScopeFor((s) => ({ ...s, [key]: scope }));
    // Re-apply the new scope to whatever is already granted on this entity.
    Object.keys(role.permissions)
      .filter((c) => c.startsWith(`${key}.`) && role.permissions[c] !== scope)
      .forEach((c) => onToggle(c, scope, true));
  }

  return (
    <div className="card admin-panel">
      <h2>{t("admin.roles.permissions")}</h2>
      <p className="muted role-hint">{t("admin.roles.permissionsHint")}</p>
      {Object.entries(registry.modules).map(([module, entities]) => (
        <details key={module} className="role-module" open={role.modules.includes(module)}>
          <summary className="role-module__sum">
            {t(`admin.roles.mod.${module}`, humanize(module))}
            <span className="role-module__count latin">
              {Object.keys(role.permissions).filter((c) => c.startsWith(`${module}.`)).length}
            </span>
          </summary>
          <div className="admin-perm-wrap">
            <table className="admin-perm role-matrix">
              <thead>
                <tr>
                  <th>{t("admin.roles.entity")}</th>
                  {registry.actions.map((a) => <th key={a}>{t(`admin.roles.act.${a}`)}</th>)}
                  <th>{t("admin.roles.scopeLabel")}</th>
                </tr>
              </thead>
              <tbody>
                {entities.map((entity) => {
                  const scope = rowScope(module, entity);
                  const anyGranted = registry.actions.some(
                    (a) => `${module}.${entity}.${a}` in role.permissions,
                  );
                  return (
                    <tr key={entity}>
                      <td>{humanize(entity)}</td>
                      {registry.actions.map((a) => {
                        const code = `${module}.${entity}.${a}`;
                        const checked = code in role.permissions;
                        return (
                          <td key={a} className="role-cell">
                            <input
                              type="checkbox"
                              checked={checked}
                              disabled={readOnly}
                              aria-label={`${humanize(entity)} ${t(`admin.roles.act.${a}`)}`}
                              onChange={() => onToggle(code, scope, !checked)}
                            />
                          </td>
                        );
                      })}
                      <td>
                        <select
                          value={scope}
                          disabled={readOnly || !anyGranted}
                          aria-label={`${humanize(entity)} ${t("admin.roles.scopeLabel")}`}
                          onChange={(e) => changeRowScope(module, entity, e.target.value)}
                        >
                          {registry.scopes.map((s) => (
                            <option key={s.value} value={s.value}>{t(`admin.scope.${s.value}`)}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </div>
  );
}

function ApprovalLimits({
  role,
  registry,
  readOnly,
  onSet,
}: {
  role: RoleDetail;
  registry: RoleRegistry;
  readOnly: boolean;
  onSet: (doc: string, value: { limit_minor: number } | { unlimited: true } | { remove: true }) => void;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  function currentLabel(doc: string): string {
    if (!(doc in role.approval_limits)) return t("admin.roles.noLimit");
    const v = role.approval_limits[doc];
    return v === null ? t("admin.roles.unlimited") : formatMinor(v);
  }

  function save(doc: string) {
    const minor = parseToMinor(drafts[doc] ?? "");
    if (minor === null || minor <= 0) return;
    onSet(doc, { limit_minor: minor });
    setDrafts((d) => ({ ...d, [doc]: "" }));
  }

  return (
    <div className="card admin-panel">
      <h2>{t("admin.roles.approvalLimits")}</h2>
      <p className="muted role-hint">{t("admin.roles.approvalLimitsHint")}</p>
      <div className="admin-perm-wrap">
        <table className="admin-perm role-limits">
          <thead>
            <tr>
              <th>{t("admin.roles.documentType")}</th>
              <th>{t("admin.roles.currentLimit")}</th>
              {!readOnly && <th>{t("admin.roles.setLimit")}</th>}
            </tr>
          </thead>
          <tbody>
            {registry.document_types.map((doc) => (
              <tr key={doc}>
                <td>{t(`admin.roles.docType.${doc}`, humanize(doc))}</td>
                <td className="latin">{currentLabel(doc)}</td>
                {!readOnly && (
                  <td className="role-limit-controls">
                    <input
                      className="latin"
                      inputMode="decimal"
                      placeholder={t("admin.roles.amount")}
                      value={drafts[doc] ?? ""}
                      onChange={(e) => setDrafts((d) => ({ ...d, [doc]: e.target.value }))}
                    />
                    <button type="button" className="btn btn--sm" onClick={() => save(doc)}>{t("admin.roles.setLimit")}</button>
                    <button type="button" className="btn btn--sm" onClick={() => onSet(doc, { unlimited: true })}>{t("admin.roles.unlimited")}</button>
                    {doc in role.approval_limits && (
                      <button type="button" className="btn btn--sm" onClick={() => onSet(doc, { remove: true })}>{t("admin.roles.remove")}</button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
