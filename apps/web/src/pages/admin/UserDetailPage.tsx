import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  getOrgUnits,
  getUser,
  resetUserPassword,
  updateUser,
  type UserDetail,
} from "../../api/users";
import { useAsync } from "../../hooks/useAsync";
import { UserStatusPill } from "./UserStatusPill";
import "./admin.css";

const STATUSES = ["active", "invited", "suspended", "archived"] as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

export function UserDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const userId = Number(id);
  const { data: org } = useAsync(getOrgUnits, [], "admin:orgunits");
  const { data, loading, error, reload } = useAsync(() => getUser(userId), [userId], `admin:user:${userId}`);
  const [notice, setNotice] = useState<string | null>(null);
  const [user, setUser] = useState<UserDetail | null>(null);

  const current = user ?? data;

  async function patch(changes: Parameters<typeof updateUser>[1]) {
    const updated = await updateUser(userId, changes);
    setUser(updated);
    reload();
  }

  async function reset() {
    const { temp_password } = await resetUserPassword(userId);
    setNotice(t("admin.detail.resetDone", { password: temp_password }));
  }

  if (loading && !current) {
    return (
      <section>
        <div className="page-skeleton" aria-busy="true">
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
        </div>
      </section>
    );
  }
  if (error) return <p className="error-text">{error}</p>;
  if (!current) return null;

  return (
    <section className="page-enter admin-detail">
      <Link to="/admin/users" className="admin-back">{t("admin.detail.back")}</Link>

      <header className="card admin-detail__head">
        <span className="admin-avatar admin-avatar--lg" aria-hidden="true">{initials(current.display_name)}</span>
        <div className="admin-detail__id">
          <h1>{current.display_name}</h1>
          <p className="latin muted">{current.email}</p>
        </div>
        <UserStatusPill status={current.status} />
      </header>

      {notice && <p className="admin-notice">{notice}</p>}

      <div className="admin-detail__grid">
        <div className="card admin-panel">
          <h2>{t("admin.detail.profile")}</h2>
          <dl className="admin-dl">
            <div><dt>{t("admin.users.name")}</dt><dd>{current.display_name}</dd></div>
            <div><dt>{t("admin.detail.username")}</dt><dd className="latin">{current.username}</dd></div>
            <div><dt>{t("admin.detail.jobTitle")}</dt><dd>{current.job_title || "—"}</dd></div>
            <div><dt>{t("admin.detail.phone")}</dt><dd className="latin">{current.phone || "—"}</dd></div>
            <div><dt>{t("admin.users.branch")}</dt><dd className="latin">{current.branch || "—"}</dd></div>
            <div><dt>{t("admin.users.department")}</dt><dd>{current.department || "—"}</dd></div>
            <div><dt>{t("admin.detail.twofa")}</dt><dd>{current.is_2fa_enabled ? t("common.on") : t("common.off")}</dd></div>
          </dl>
        </div>

        <div className="card admin-panel">
          <h2>{t("admin.detail.roleAccess")}</h2>
          <label className="admin-field">
            <span>{t("admin.detail.assignedRole")}</span>
            <select value={current.role ?? ""} onChange={(e) => patch({ role: e.target.value })}>
              <option value="">{t("admin.invite.noRole")}</option>
              {org?.roles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="admin-field">
            <span>{t("admin.users.status")}</span>
            <select value={current.status} onChange={(e) => patch({ status: e.target.value })}>
              {STATUSES.map((s) => <option key={s} value={s}>{t(`admin.status.${s}`)}</option>)}
            </select>
          </label>
          <label className="admin-field">
            <span>{t("admin.users.department")}</span>
            <select value={current.department ?? ""} onChange={(e) => patch({ department: e.target.value || null })}>
              <option value="">—</option>
              {org?.departments.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
            </select>
          </label>
          <button className="btn admin-reset" onClick={reset}>{t("admin.detail.resetPassword")}</button>
        </div>

        <div className="card admin-panel">
          <h2>{t("admin.detail.modules")}</h2>
          {current.modules.length === 0 ? (
            <p className="muted">{t("admin.detail.noModules")}</p>
          ) : (
            <ul className="admin-chips">
              {current.modules.map((m) => <li key={m} className="admin-chip">{t(`nav.${m}`, m)}</li>)}
            </ul>
          )}
        </div>

        <div className="card admin-panel">
          <h2>{t("admin.detail.permissions")}</h2>
          {current.permissions.length === 0 ? (
            <p className="muted">{t("admin.detail.noPermissions")}</p>
          ) : (
            <div className="admin-perm-wrap">
              <table className="admin-perm">
                <tbody>
                  {current.permissions.map((p) => (
                    <tr key={p.code}>
                      <td className="latin">{p.code}</td>
                      <td className="muted">{t(`admin.scope.${p.scope}`, p.scope)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card admin-panel">
          <h2>{t("admin.detail.sessions")}</h2>
          {current.sessions.length === 0 ? (
            <p className="muted">{t("admin.detail.noSessions")}</p>
          ) : (
            <ul className="admin-log">
              {current.sessions.map((s, i) => (
                <li key={i}>
                  <span className="latin">{s.at.slice(0, 16).replace("T", " ")}</span>
                  <span className="muted">{s.action}</span>
                  <span className={s.result === "success" ? "admin-ok" : "admin-bad"}>{s.result}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card admin-panel">
          <h2>{t("admin.detail.audit")}</h2>
          {current.audit.length === 0 ? (
            <p className="muted">{t("admin.detail.noAudit")}</p>
          ) : (
            <ul className="admin-log">
              {current.audit.map((a, i) => (
                <li key={i}>
                  <span className="latin">{a.at.slice(0, 16).replace("T", " ")}</span>
                  <span className="muted">{a.module}.{a.action}</span>
                  <span className="latin admin-log__ent">{a.entity_type}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
