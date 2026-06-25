import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  getOrgUnits,
  getUser,
  resetUserPassword,
  revokeAllSessions,
  revokeSession,
  updateUser,
  type UserDetail,
} from "../../api/users";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { UserStatusPill } from "./UserStatusPill";
import { ListSkeleton } from "../../components/ListSkeleton";
import { InlineEdit } from "../../components/InlineEdit";
import "./admin.css";

const STATUSES = ["active", "invited", "suspended", "archived"] as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

export function UserDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams();
  const userId = Number(id);
  const { data: org } = useAsync(getOrgUnits, [], "admin:orgunits");
  const { data, loading, error, reload, mutate } = useAsync<UserDetail>(
    () => getUser(userId),
    [userId],
    `admin:user:${userId}`,
  );
  const [notice, setNotice] = useState<string | null>(null);

  const current = data;

  // Optimistic field edit: reflect the role/status/department change in the dropdown immediately,
  // settle with the server's user, roll back + toast on failure. No success toast — these dropdowns
  // are edited freely and shouldn't spam.
  function patch(changes: Parameters<typeof updateUser>[1]) {
    if (!data) return;
    void runOptimistic<UserDetail, UserDetail>({
      current: data,
      mutate,
      optimistic: (u) => ({ ...u, ...changes }) as UserDetail,
      request: () => updateUser(userId, changes),
      settle: (_predicted, updated) => updated,
      toast,
    });
  }

  // Inline text edits (job title / phone): same optimistic flow, but confirm the save with a toast
  // once it lands — text fields are edited deliberately, so the "Saved" acknowledgement is welcome
  // (unlike the freely-flicked dropdowns above, which stay silent). Awaited so the field stays in
  // its saving state until the round-trip settles.
  function saveField(changes: Parameters<typeof updateUser>[1]) {
    if (!data) return Promise.resolve();
    return runOptimistic<UserDetail, UserDetail>({
      current: data,
      mutate,
      optimistic: (u) => ({ ...u, ...changes }) as UserDetail,
      request: () => updateUser(userId, changes),
      settle: (_predicted, updated) => updated,
      toast,
      success: t("common.saved"),
    });
  }

  async function reset() {
    const { temp_password } = await resetUserPassword(userId);
    setNotice(t("admin.detail.resetDone", { password: temp_password }));
  }

  async function revokeOne(tokenId: number) {
    mutate(await revokeSession(userId, tokenId));
    toast.show(t("admin.detail.sessionRevoked"), "success");
  }

  async function revokeAll() {
    const { revoked } = await revokeAllSessions(userId);
    reload();
    toast.show(t("admin.detail.allSessionsRevoked", { count: revoked }), "success");
  }

  if (loading && !current) {
    return (
      <section>
        <ListSkeleton rows={1} />
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
            <div className="admin-dl__edit">
              <dt>{t("admin.users.name")}</dt>
              <dd>
                <InlineEdit
                  value={current.display_name}
                  label={t("admin.users.name")}
                  placeholder={t("admin.detail.namePlaceholder")}
                  onSave={(v) => saveField({ display_name: v })}
                />
              </dd>
            </div>
            <div><dt>{t("admin.detail.username")}</dt><dd className="latin">{current.username}</dd></div>
            <div className="admin-dl__edit">
              <dt>{t("admin.detail.jobTitle")}</dt>
              <dd>
                <InlineEdit
                  value={current.job_title}
                  label={t("admin.detail.jobTitle")}
                  placeholder={t("admin.detail.jobTitlePlaceholder")}
                  onSave={(v) => saveField({ job_title: v })}
                />
              </dd>
            </div>
            <div className="admin-dl__edit">
              <dt>{t("admin.detail.phone")}</dt>
              <dd>
                <InlineEdit
                  value={current.phone}
                  label={t("admin.detail.phone")}
                  placeholder={t("admin.detail.phonePlaceholder")}
                  inputClassName="latin"
                  onSave={(v) => saveField({ phone: v })}
                />
              </dd>
            </div>
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
          <div className="admin-panel__head">
            <h2>{t("admin.detail.activeSessions")}</h2>
            {current.active_sessions.length > 0 && (
              <button className="btn btn--sm btn--danger" onClick={revokeAll}>{t("admin.detail.revokeAll")}</button>
            )}
          </div>
          {current.active_sessions.length === 0 ? (
            <p className="muted">{t("admin.detail.noActiveSessions")}</p>
          ) : (
            <ul className="admin-log">
              {current.active_sessions.map((s) => (
                <li key={s.id}>
                  <span className="latin">{s.created_at ? s.created_at.slice(0, 16).replace("T", " ") : "—"}</span>
                  <span className="muted">{t("admin.detail.expires")}: {s.expires_at ? s.expires_at.slice(0, 10) : "—"}</span>
                  <button className="btn btn--sm admin-log__ent" onClick={() => revokeOne(s.id)}>{t("admin.detail.revoke")}</button>
                </li>
              ))}
            </ul>
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
