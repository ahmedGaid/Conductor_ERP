import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { bulkUsers, createUser, getOrgUnits, getUser, listUsers } from "../../api/users";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { normalizeSearch } from "../../lib/arabicSearch";
import { EmptyState } from "../../components/EmptyState";
import { UserStatusPill } from "./UserStatusPill";
import "./admin.css";

const STATUSES = ["active", "invited", "suspended", "archived"] as const;

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
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);

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

  function toggle(id: number) {
    setSelected((cur) => {
      const next = new Set(cur);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  // A bulk action touches the selected set server-side and returns only a count, so it stays a
  // round-trip: run it, clear the selection, refresh, and report the count via toast.
  async function runBulk(action: "suspend" | "activate" | "archive") {
    try {
      const { affected } = await bulkUsers(action, [...selected]);
      setSelected(new Set());
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

      <InviteForm org={org} onCreated={(msg) => { setNotice(msg); reload(); }} />
      {notice && <p className="admin-notice">{notice}</p>}

      <div className="card admin-filters">
        <input
          type="search"
          placeholder={t("admin.users.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)} aria-label={t("admin.users.role")}>
          <option value="">{t("admin.users.allRoles")}</option>
          {org?.roles.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={department} onChange={(e) => setDepartment(e.target.value)} aria-label={t("admin.users.department")}>
          <option value="">{t("admin.users.allDepartments")}</option>
          {org?.departments.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t("admin.users.status")}>
          <option value="">{t("admin.users.allStatuses")}</option>
          {STATUSES.map((s) => <option key={s} value={s}>{t(`admin.status.${s}`)}</option>)}
        </select>
      </div>

      {selected.size > 0 && (
        <div className="card admin-bulkbar">
          <span>{t("admin.selected", { count: selected.size })}</span>
          <div className="admin-bulkbar__actions">
            <button className="btn btn--sm" onClick={() => runBulk("activate")}>{t("admin.action.activate")}</button>
            <button className="btn btn--sm" onClick={() => runBulk("suspend")}>{t("admin.action.suspend")}</button>
            <button className="btn btn--sm" onClick={() => runBulk("archive")}>{t("admin.action.archive")}</button>
          </div>
        </div>
      )}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {users && filtered.length === 0 && <EmptyState title={t("admin.users.empty")} hint={t("admin.users.emptyHint")} />}

      {filtered.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th aria-label={t("admin.select")}></th>
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
              {filtered.map((u) => (
                <tr
                  key={u.id}
                  className="admin-row"
                  onClick={() => navigate(`/admin/users/${u.id}`)}
                  onMouseEnter={() => prefetch(`admin:user:${u.id}`, () => getUser(u.id))}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(u.id)}
                      onChange={() => toggle(u.id)}
                      aria-label={u.username}
                    />
                  </td>
                  <td>
                    <span className="admin-id">
                      <span className="admin-avatar" aria-hidden="true">{initials(u.display_name)}</span>
                      <span className="admin-id__name">{u.display_name}</span>
                    </span>
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
    </section>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

function InviteForm({
  org,
  onCreated,
}: {
  org: import("../../api/users").OrgUnits | null;
  onCreated: (msg: string) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
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
      setUsername(""); setEmail(""); setRole(""); setDepartment(""); setOpen(false);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="admin-invite-cta">
        <button className="btn btn--primary" onClick={() => setOpen(true)}>{t("admin.invite.cta")}</button>
      </div>
    );
  }

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
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">{t("admin.invite.noRole")}</option>
            {org?.roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="admin-field">
          <span>{t("admin.users.department")}</span>
          <select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">—</option>
            {org?.departments.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
          </select>
        </label>
      </div>
      {err && <p className="error-text">{err}</p>}
      <div className="admin-invite__foot">
        <button type="button" className="btn" onClick={() => setOpen(false)}>{t("common.cancel")}</button>
        <button type="submit" className="btn btn--primary" disabled={busy}>{t("admin.invite.submit")}</button>
      </div>
    </form>
  );
}
