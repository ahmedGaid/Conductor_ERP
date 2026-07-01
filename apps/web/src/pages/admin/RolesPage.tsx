import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createRole, listRoles, type RoleRow } from "../../api/roles";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./admin.css";

export function RolesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: roles, loading, error, reload } = useAsync(listRoles, [], "admin:roles");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<RoleRow>[]>(
    () => [
      { key: "name", label: t("admin.roles.name"), type: "text", accessor: (r) => r.name },
      {
        key: "kind",
        label: t("admin.roles.kind"),
        type: "select",
        options: [
          { value: "builtin", label: t("admin.roles.builtin") },
          { value: "custom", label: t("admin.roles.custom") },
        ],
        accessor: (r) => (r.protected ? "builtin" : "custom"),
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (roles ? roles.filter((r) => matchesAllFilters(r, fields, filters)) : roles),
    [roles, fields, filters],
  );

  // j/k move a row highlight, Enter/o opens the role detail page (rows are already click-to-open).
  const { active } = useListKeyboardNav<RoleRow>({
    items: filtered ?? [],
    onOpen: (r) => navigate(`/admin/roles/${encodeURIComponent(r.name)}`),
    persistKey: "admin:roles",
    getItemId: (r) => r.name,
  });

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("admin.roles.title")}</h1>
        <p className="module-head__desc">{t("admin.roles.intro")}</p>
      </header>

      <NewRoleForm roles={roles ?? []} onCreated={(name) => navigate(`/admin/roles/${encodeURIComponent(name)}`)} />

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {roles && roles.length === 0 && (
        <EmptyState title={t("admin.roles.empty")} hint={t("admin.roles.emptyHint")} />
      )}

      {roles && roles.length > 0 && (
        <div className="admin-filterbar">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {roles && roles.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
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
              {filtered.map((r, i) => (
                <tr
                  key={r.name}
                  className="admin-row"
                  data-kbd-active={i === active ? "true" : undefined}
                  aria-selected={i === active}
                  onClick={() => navigate(`/admin/roles/${encodeURIComponent(r.name)}`)}
                >
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
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [copyFrom, setCopyFrom] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const created = await createRole(name.trim(), copyFrom || undefined);
      toast.show(t("admin.roles.created"), "success");
      onCreated(created.name);
    } catch (e2) {
      toast.show(e2 instanceof Error ? e2.message : String(e2), "error");
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
      <div className="admin-invite__foot">
        <button type="button" className="btn" onClick={() => setOpen(false)}>{t("common.cancel")}</button>
        <button type="submit" className="btn btn--primary" disabled={busy}>{t("admin.roles.create")}</button>
      </div>
    </form>
  );
}
