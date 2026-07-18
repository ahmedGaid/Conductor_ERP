import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "../../components/Badge";
import { ComboBox } from "../../components/ComboBox";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import {
  createApiKey,
  listApiKeys,
  listApiRoutes,
  revokeApiKey,
  type ApiKeyRow,
  type ApiKeyWithSecret,
} from "../../api/apiKeys";
import { getMe } from "../../api/identity";
import { listRoles } from "../../api/roles";
import { useToast } from "../../app/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { runOptimistic } from "../../lib/optimistic";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import "../admin/admin.css";

let tempSeq = 0;

function formatDate(value: string | null): string {
  if (!value) return "";
  return new Date(value).toLocaleDateString();
}

function ReferencePanel() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listApiRoutes, [], "settings:apiDocs");

  return (
    <div className="card setcard">
      <p className="setrow__title">{t("settings.developers.docsTitle")}</p>
      <p className="setrow__desc">{t("settings.developers.docsLead")}</p>

      <div className="setrow__desc setcard__block">
        <strong>{t("settings.developers.docsAuthTitle")}</strong>
        <p>{t("settings.developers.docsAuthBody")}</p>
        <code className="latin webhook-secret">Authorization: Api-Key ck_your_key_here</code>
      </div>
      <p className="setrow__desc">{t("settings.developers.docsRateLimitNote")}</p>
      <p className="setrow__desc">{t("settings.developers.docsMoneyNote")}</p>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("settings.developers.docsPath")}</th>
                <th>{t("settings.developers.docsMethods")}</th>
              </tr>
            </thead>
            <tbody>
              {data.routes.map((r) => (
                <tr key={r.path} className="admin-row">
                  <td className="latin">/{r.path}</td>
                  <td className="latin">{r.methods.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ApiKeysPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data: me } = useAsync(getMe, []);
  const { data: roles } = useAsync(listRoles, [], "settings:roles");
  const { data, loading, error, reload, mutate } = useAsync(listApiKeys, [], "settings:apiKeys");

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [revealedSecret, setRevealedSecret] = useState<{ secret: string; role: string } | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyRow | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.developers.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!me || loading) return <SettingsSkeleton />;

  const roleOptions = (roles ?? []).map((r) => ({ value: r.name, label: r.name }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || !role) return;
    const tempId = -(++tempSeq);
    const created = await runOptimistic<ApiKeyRow[], ApiKeyWithSecret>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => [
        {
          id: tempId, name: trimmed, prefix: "", role, created_at: new Date().toISOString(),
          expires_at: null, last_used_at: null, is_active: true,
        },
        ...rows,
      ],
      request: () => createApiKey({ name: trimmed, role }),
      settle: (rows, result) => rows.map((r) => (r.id === tempId ? result : r)),
      toast,
      success: t("settings.developers.toastCreated"),
    });
    if (created) {
      setRevealedSecret({ secret: created.secret, role: created.role });
      setName("");
      setRole("");
    }
  }

  function revoke(key: ApiKeyRow) {
    void runOptimistic<ApiKeyRow[], ApiKeyRow>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((r) => (r.id === key.id ? { ...r, is_active: false } : r)),
      request: () => revokeApiKey(key.id),
      settle: (rows, updated) => rows.map((r) => (r.id === updated.id ? updated : r)),
      toast,
      success: t("settings.developers.toastRevoked"),
    });
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <p className="setrow__desc setcard__lead">{t("settings.developers.lead")}</p>

      <h2 className="setrow__title">{t("settings.developers.keysTitle")}</h2>

      {revealedSecret && (
        <div className="card setcard" role="status">
          <p className="setrow__title">{t("settings.developers.secretRevealTitle")}</p>
          <p className="setrow__desc">
            {t("settings.developers.secretRevealDesc", { role: revealedSecret.role })}
          </p>
          <code className="latin webhook-secret">{revealedSecret.secret}</code>
          <div className="admin-invite__foot">
            <button className="btn btn--ghost" type="button" onClick={() => setRevealedSecret(null)}>
              {t("settings.developers.secretRevealDismiss")}
            </button>
          </div>
        </div>
      )}

      <form ref={formRef} className="card admin-invite" onSubmit={(e) => void onSubmit(e)}>
        <div className="admin-invite__grid">
          <label className="admin-field">
            <span>{t("settings.developers.name")}</span>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="admin-field">
            <span>{t("settings.developers.role")}</span>
            <ComboBox
              options={roleOptions}
              value={role}
              onChange={setRole}
              placeholder={t("settings.developers.rolePlaceholder")}
            />
          </label>
        </div>
        <div className="admin-invite__foot">
          <button className="btn btn--primary" type="submit" disabled={!name.trim() || !role}>
            {t("settings.developers.add")}
          </button>
        </div>
      </form>

      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState
          title={t("settings.developers.empty")}
          hint={t("settings.developers.emptyHint")}
        />
      )}

      {data && data.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("settings.developers.name")}</th>
                <th>{t("settings.developers.role")}</th>
                <th>{t("settings.developers.prefix")}</th>
                <th>{t("settings.developers.lastUsed")}</th>
                <th>{t("settings.developers.status")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((k) => (
                <tr key={k.id} className="admin-row">
                  <td>{k.name}</td>
                  <td className="latin">{k.role}</td>
                  <td className="latin">{k.prefix}</td>
                  <td className="latin">
                    {k.last_used_at ? formatDate(k.last_used_at) : t("settings.developers.usedNever")}
                  </td>
                  <td>
                    <Badge tone={k.is_active ? "completed" : "neutral"}>
                      {k.is_active
                        ? t("settings.developers.statusActive")
                        : t("settings.developers.statusRevoked")}
                    </Badge>
                  </td>
                  <td>
                    {k.is_active && (
                      <button
                        className="btn btn--ghost"
                        type="button"
                        onClick={() => setRevokeTarget(k)}
                      >
                        {t("settings.developers.revoke")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ReferencePanel />

      <ConfirmDialog
        open={revokeTarget !== null}
        title={t("settings.developers.revokeConfirmTitle")}
        body={t("settings.developers.revokeConfirmBody")}
        confirmLabel={t("settings.developers.revoke")}
        danger
        onConfirm={() => {
          if (revokeTarget) revoke(revokeTarget);
        }}
        onClose={() => setRevokeTarget(null)}
      />
    </section>
  );
}
