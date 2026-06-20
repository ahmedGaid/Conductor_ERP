import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createRole, listRoles, type RoleRow } from "../../api/roles";
import { useAsync } from "../../hooks/useAsync";
import { EmptyState } from "../../components/EmptyState";
import "./admin.css";

export function RolesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: roles, loading, error } = useAsync(listRoles, [], "admin:roles");

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("admin.roles.title")}</h1>
        <p className="module-head__desc">{t("admin.roles.intro")}</p>
      </header>

      <NewRoleForm roles={roles ?? []} onCreated={(name) => navigate(`/admin/roles/${encodeURIComponent(name)}`)} />

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {roles && roles.length === 0 && (
        <EmptyState title={t("admin.roles.empty")} hint={t("admin.roles.emptyHint")} />
      )}

      {roles && roles.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("admin.roles.name")}</th>
                <th>{t("admin.roles.kind")}</th>
                <th>{t("admin.roles.members")}</th>
                <th>{t("admin.roles.permissionCount")}</th>
                <th>{t("admin.roles.modules")}</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.name} className="admin-row" onClick={() => navigate(`/admin/roles/${encodeURIComponent(r.name)}`)}>
                  <td><span className="admin-id__name">{r.name}</span></td>
                  <td>
                    <span className={`upill ${r.protected ? "upill--invited" : "upill--active"}`}>
                      {t(r.protected ? "admin.roles.builtin" : "admin.roles.custom")}
                    </span>
                  </td>
                  <td className="latin">{r.members}</td>
                  <td className="latin">{r.permission_count}</td>
                  <td className="latin muted">{r.modules.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function NewRoleForm({ roles, onCreated }: { roles: RoleRow[]; onCreated: (name: string) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [copyFrom, setCopyFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const created = await createRole(name.trim(), copyFrom || undefined);
      onCreated(created.name);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="admin-invite-cta">
        <button className="btn btn--primary" onClick={() => setOpen(true)}>{t("admin.roles.create")}</button>
      </div>
    );
  }

  return (
    <form className="card admin-invite" onSubmit={submit}>
      <div className="admin-invite__grid">
        <label className="admin-field">
          <span>{t("admin.roles.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="admin-field">
          <span>{t("admin.roles.copyFrom")}</span>
          <select value={copyFrom} onChange={(e) => setCopyFrom(e.target.value)}>
            <option value="">{t("admin.roles.copyBlank")}</option>
            {roles.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
          </select>
        </label>
      </div>
      {err && <p className="error-text">{err}</p>}
      <div className="admin-invite__foot">
        <button type="button" className="btn" onClick={() => setOpen(false)}>{t("common.cancel")}</button>
        <button type="submit" className="btn btn--primary" disabled={busy}>{t("admin.roles.create")}</button>
      </div>
    </form>
  );
}
