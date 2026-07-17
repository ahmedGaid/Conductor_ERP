import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { bulkUsers, createUser, getOrgUnits, getUser, listUsers } from "../../api/users";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { normalizeSearch } from "../../lib/arabicSearch";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { EmptyState } from "../../components/EmptyState";
import { ComboBox } from "../../components/ComboBox";
import { UserStatusPill } from "./UserStatusPill";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./admin.css";

const STATUSES = ["active", "invited", "suspended", "archived"] as const;
type UserRow = Awaited<ReturnType<typeof listUsers>>[number];

export function UsersPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { data: users, loading, error, reload } = useAsync(() => listUsers(), [], "admin:users");
  const { data: org } = useAsync(getOrgUnits, [], "admin:orgunits");

  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [department, setDepartment] = useState("");
  const [assignRoleTo, setAssignRoleTo] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);

  const filtered = useMemo(() => {
    const term = normalizeSearch(search.trim());
    return (users ?? []).filter((u) => {
      if (term && !normalizeSearch(`${u.username} ${u.email} ${u.display_name}`).includes(term)) return false;
      if (role && u.role !== role) return false;
      if (status && u.status !== status) return false;
      if (department && u.department !== department) return false;
      return true;
    });
  }, [users, search, role, status, department]);

  // j/k move a row highlight, Enter/o opens the user detail page (rows are already click-to-open).
  const { active } = useListKeyboardNav({
    items: filtered,
    onOpen: (u) => navigate(`/admin/users/${u.id}`),
    persistKey: "admin:users",
    getItemId: (u) => String(u.id),
  });

  const csvColumns = useMemo<CsvColumn<UserRow>[]>(
    () => [
      { header: t("admin.users.name"), accessor: (u) => u.display_name },
      { header: t("admin.users.email"), accessor: (u) => u.email },
      { header: t("admin.users.role"), accessor: (u) => u.role ?? "" },
      { header: t("admin.users.department"), accessor: (u) => u.department ?? "" },
      { header: t("admin.users.status"), accessor: (u) => t(`admin.status.${u.status}`) },
      { header: t("admin.users.lastLogin"), accessor: (u) => (u.last_login ? u.last_login.slice(0, 10) : "") },
    ],
    [t],
  );
  const listPrimary = useMemo(
    () => ({ label: t("admin.invite.cta"), onClick: () => setInviteOpen(true) }),
    [t],
  );
  useListPageActions({ primary: listPrimary, rows: filtered, columns: csvColumns, filename: "users" });

  // Multi-select for bulk suspend/activate/archive/assign-role via the identity bulk endpoint.
  const selection = useRowSelection<UserRow>({
    items: filtered,
    getItemId: (u) => String(u.id),
    activeIndex: active,
  });

  // A bulk action touches the selected set server-side and returns only a count, so it stays a
  // round-trip: run it, clear the selection, refresh, and report the count via toast.
  async function runBulk(action: "suspend" | "activate" | "archive" | "assign_role") {
    try {
      const ids = selection.selectedItems.map((u) => u.id);
      const { affected } = await bulkUsers(action, ids, action === "assign_role" ? assignRoleTo : undefined);
      selection.clear();
      reload();
      toast.show(t("admin.bulkDone", { count: affected }), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("admin.users.title")}</h1>
        <p className="module-head__desc">{t("admin.users.intro")}</p>
      </header>

      <InviteForm org={org} open={inviteOpen} onClose={() => setInviteOpen(false)} onCreated={(msg) => { setNotice(msg); reload(); }} />

      {notice && <p className="admin-notice">{notice}</p>}

      <div className="card admin-filters">
        <input
          type="search"
          placeholder={t("admin.users.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <ComboBox
          value={role}
          onChange={setRole}
          placeholder={t("admin.users.allRoles")}
          options={[{ value: "", label: t("admin.users.allRoles") }, ...(org?.roles.map((r) => ({ value: r, label: r })) ?? [])]}
          aria-label={t("admin.users.role")}
        />
        <ComboBox
          value={department}
          onChange={setDepartment}
          placeholder={t("admin.users.allDepartments")}
          options={[{ value: "", label: t("admin.users.allDepartments") }, ...(org?.departments.map((d) => ({ value: d.code, label: d.name })) ?? [])]}
          aria-label={t("admin.users.department")}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t("admin.users.status")}>
          <option value="">{t("admin.users.allStatuses")}</option>
          {STATUSES.map((s) => <option key={s} value={s}>{t(`admin.status.${s}`)}</option>)}
        </select>
      </div>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {users && filtered.length === 0 && <EmptyState title={t("admin.users.empty")} hint={t("admin.users.emptyHint")} />}

      {filtered.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="admin-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("admin.users.name")}</th>
                <th>{t("admin.users.email")}</th>
                <th>{t("admin.users.role")}</th>
                <th>{t("admin.users.department")}</th>
                <th>{t("admin.users.branch")}</th>
                <th>{t("admin.users.status")}</th>
                <th>{t("admin.users.lastLogin")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u, i) => (
                <tr
                  key={u.id}
                  className="admin-row"
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(String(u.id)) ? "true" : undefined}
                  aria-selected={selection.isSelected(String(u.id)) || i === active}
                >
                  <SelectRowCell
                    className="admin-table__select"
                    checked={selection.isSelected(String(u.id))}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <Link
                      to={`/admin/users/${u.id}`}
                      className="admin-id"
                      onMouseEnter={() => prefetch(`admin:user:${u.id}`, () => getUser(u.id))}
                      onFocus={() => prefetch(`admin:user:${u.id}`, () => getUser(u.id))}
                    >
                      <span className="admin-avatar" aria-hidden="true">{initials(u.display_name)}</span>
                      <span className="admin-id__name">{u.display_name}</span>
                    </Link>
                  </td>
                  <td className="latin muted">{u.email}</td>
                  <td>{u.role ?? "—"}</td>
                  <td>{u.department ?? "—"}</td>
                  <td className="latin">{u.branch ?? "—"}</td>
                  <td><UserStatusPill status={u.status} /></td>
                  <td className="latin muted">{u.last_login ? u.last_login.slice(0, 10) : t("admin.users.never")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button className="btn btn--sm" onClick={() => runBulk("activate")}>{t("admin.action.activate")}</button>
        <button className="btn btn--sm" onClick={() => runBulk("suspend")}>{t("admin.action.suspend")}</button>
        <button className="btn btn--sm" onClick={() => runBulk("archive")}>{t("admin.action.archive")}</button>
        <ComboBox
          value={assignRoleTo}
          onChange={setAssignRoleTo}
          placeholder={t("admin.action.assignRole")}
          options={[{ value: "", label: t("admin.action.assignRole") }, ...(org?.roles.map((r) => ({ value: r, label: r })) ?? [])]}
          aria-label={t("admin.action.assignRole")}
        />
        <button className="btn btn--sm" disabled={!assignRoleTo} onClick={() => runBulk("assign_role")}>
          {t("admin.action.apply")}
        </button>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("users-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

function InviteForm({
  org,
  open,
  onClose,
  onCreated,
}: {
  org: import("../../api/users").OrgUnits | null;
  open: boolean;
  onClose: () => void;
  onCreated: (msg: string) => void;
}) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [department, setDepartment] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const created = await createUser({ username, email, role: role || undefined, department: department || undefined });
      onCreated(t("admin.invite.done", { name: username, password: created.temp_password ?? "" }));
      setUsername(""); setEmail(""); setRole(""); setDepartment(""); onClose();
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <form className="card admin-invite" onSubmit={submit}>
      <div className="admin-invite__grid">
        <label className="admin-field">
          <span>{t("admin.invite.username")}</span>
          <input className="latin" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label className="admin-field">
          <span>{t("admin.invite.email")}</span>
          <input className="latin" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="admin-field">
          <span>{t("admin.users.role")}</span>
          <ComboBox
            value={role}
            onChange={setRole}
            placeholder={t("admin.invite.noRole")}
            options={[{ value: "", label: t("admin.invite.noRole") }, ...(org?.roles.map((r) => ({ value: r, label: r })) ?? [])]}
          />
        </label>
        <label className="admin-field">
          <span>{t("admin.users.department")}</span>
          <ComboBox
            value={department}
            onChange={setDepartment}
            placeholder={t("common.selectField", { field: t("admin.users.department") })}
            options={(org?.departments ?? []).map((d) => ({ value: d.code, label: d.name }))}
          />
        </label>
      </div>
      {err && <p className="error-text">{err}</p>}
      <div className="admin-invite__foot">
        <button type="button" className="btn" onClick={onClose}>{t("common.cancel")}</button>
        <button type="submit" className="btn btn--primary" disabled={busy}>{t("admin.invite.submit")}</button>
      </div>
    </form>
  );
}
