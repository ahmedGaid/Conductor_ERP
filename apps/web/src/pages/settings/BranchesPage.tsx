import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { getMe } from "../../api/identity";
import { createBranch, listBranches, updateBranch, type Branch } from "../../api/branches";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../../lib/optimistic";
import { localizedName } from "../../lib/bilingualName";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import { Toggle } from "./controls";
import "../admin/admin.css";

export function BranchesPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const toast = useToast();
  const { data: me } = useAsync(getMe, []);
  const { data, loading, error, errorStatus, reload, mutate } = useAsync(listBranches, [], "settings:branches");

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [nameAr, setNameAr] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  useSetHelpSignals({ branchCount: (data ?? []).length });

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.branches.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!me || loading) return <SettingsSkeleton />;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    const na = nameAr.trim();
    if (!c || !n) return;
    void optimisticCreate<Branch>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, name_ar: na, is_active: true }) as Branch,
      request: () => createBranch({ code: c, name: n, name_ar: na }),
      toast,
      success: t("settings.branches.toastCreated"),
    });
    setCode("");
    setName("");
    setNameAr("");
  }

  function toggleActive(branch: Branch) {
    const next = !branch.is_active;
    void runOptimistic<Branch[], Branch>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((b) => (b.id === branch.id ? { ...b, is_active: next } : b)),
      request: () => updateBranch(branch.code, { is_active: next }),
      settle: (rows, updated) => rows.map((b) => (b.id === updated.id ? updated : b)),
      toast,
      success: t("settings.branches.toastUpdated"),
    });
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <p className="setrow__desc setcard__lead">{t("settings.branches.lead")}</p>

      <form ref={formRef} className="card admin-invite" onSubmit={onSubmit}>
        <div className="admin-invite__grid">
          <label className="admin-field">
            <span>{t("settings.branches.code")}</span>
            <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
          </label>
          <label className="admin-field">
            <span>{t("settings.branches.name")}</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="admin-field">
            {/* Optional — a branch with no Arabic name reads in English on Arabic screens. */}
            <span>{t("settings.branches.nameAr")}</span>
            <input
              dir="rtl"
              lang="ar"
              value={nameAr}
              onChange={(e) => setNameAr(e.target.value)}
              placeholder={t("settings.branches.nameArHint")}
            />
          </label>
        </div>
        <div className="admin-invite__foot">
          <button className="btn btn--primary" type="submit">
            {t("settings.branches.add")}
          </button>
        </div>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} status={errorStatus} />}

      {data && data.length === 0 && (
        <EmptyState title={t("settings.branches.empty")} hint={t("settings.branches.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("settings.branches.code")}</th>
                <th>{t("settings.branches.name")}</th>
                <th>{t("settings.branches.active")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((b) => (
                <tr key={b.id} className="admin-row">
                  <td className="latin">{b.code}</td>
                  {/* dir="auto" — a branch may still carry only an English name on an Arabic screen. */}
                  <td dir="auto">{localizedName(b, lang)}</td>
                  <td>
                    <Toggle
                      checked={b.is_active}
                      onChange={() => toggleActive(b)}
                      label={t("settings.branches.active")}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
