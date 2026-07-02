import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../../components/BackLink";

import { disposeAsset, getAsset, type FixedAsset } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

export function FixedAssetDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { code = "" } = useParams();
  const { data: asset, loading, error, reload, mutate } = useAsync<FixedAsset>(() => getAsset(code), [code], `accounting:asset:${code}`);

  const [disposeDate, setDisposeDate] = useState(new Date().toISOString().slice(0, 10));
  const [proceeds, setProceeds] = useState("0");
  const [formError, setFormError] = useState<string | null>(null);

  // Optimistic disposal: flip the asset to "disposed" so the badge swaps and the form hides at once,
  // then let the server's asset reconcile the gain/loss and journal number. Failure rolls back + toasts.
  function onDispose(e: FormEvent) {
    e.preventDefault();
    const proceedsMinor = parseToMinor(proceeds);
    if (proceedsMinor === null || proceedsMinor < 0) {
      setFormError(t("accounting.assets.invalidInput"));
      return;
    }
    setFormError(null);
    if (!asset) return;
    void runOptimistic<FixedAsset, FixedAsset>({
      current: asset,
      mutate,
      optimistic: (a) => ({ ...a, status: "disposed" }),
      request: () => disposeAsset(code, { disposed_date: disposeDate, proceeds_minor: proceedsMinor }),
      settle: (_predicted, updated) => updated,
      toast,
      success: t("accounting.toast.assetDisposed"),
    });
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <BackLink to="/accounting/assets">{t("accounting.assets.backToList")}</BackLink>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {asset && (
        <>
          <div className="card acct-detail">
            <header className="acct-detail__head">
              <div>
                <h2><Bdi>{asset.code}</Bdi> — {asset.name}</h2>
                <Badge tone={asset.status === "active" ? "running" : "completed"}>
                  {t(`accounting.assets.statuses.${asset.status}`)}
                </Badge>
              </div>
            </header>

            <dl className="acct-detail__grid">
              <div><dt>{t("accounting.assets.cost")}</dt><dd><Bdi>{formatMinor(asset.cost_minor)}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.salvage")}</dt><dd><Bdi>{formatMinor(asset.salvage_minor)}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.life")}</dt><dd><Bdi>{asset.useful_life_months}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.acquired")}</dt><dd><Bdi>{asset.acquisition_date}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.accumulated")}</dt><dd><Bdi>{formatMinor(asset.accumulated_depreciation_minor)}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.nbv")}</dt><dd><Bdi>{formatMinor(asset.net_book_value_minor)}</Bdi></dd></div>
              <div><dt>{t("accounting.assets.monthsDepreciated")}</dt><dd><Bdi>{asset.months_depreciated}</Bdi></dd></div>
              {asset.acquire_journal_number && (
                <div><dt>{t("accounting.assets.acquireEntry")}</dt><dd><Bdi>{asset.acquire_journal_number}</Bdi></dd></div>
              )}
            </dl>

            {asset.status === "disposed" && (
              <dl className="acct-detail__grid acct-detail__disposal">
                <div><dt>{t("accounting.assets.disposedDate")}</dt><dd><Bdi>{asset.disposed_date}</Bdi></dd></div>
                <div><dt>{t("accounting.assets.proceeds")}</dt><dd><Bdi>{formatMinor(asset.disposal_proceeds_minor ?? 0)}</Bdi></dd></div>
                <div>
                  <dt>{(asset.disposal_gain_loss_minor ?? 0) >= 0 ? t("accounting.assets.gain") : t("accounting.assets.loss")}</dt>
                  <dd><Bdi>{formatMinor(Math.abs(asset.disposal_gain_loss_minor ?? 0))}</Bdi></dd>
                </div>
                {asset.disposal_journal_number && (
                  <div><dt>{t("accounting.assets.disposalEntry")}</dt><dd><Bdi>{asset.disposal_journal_number}</Bdi></dd></div>
                )}
              </dl>
            )}
          </div>

          {asset.status === "active" && (
            <form className="card acct-toolbar" onSubmit={onDispose}>
              <h3 className="acct-detail__action-title">{t("accounting.assets.dispose")}</h3>
              <label className="acct-field">
                <span>{t("accounting.assets.disposedDate")}</span>
                <input className="latin" type="date" value={disposeDate} onChange={(e) => setDisposeDate(e.target.value)} required />
              </label>
              <label className="acct-field">
                <span>{t("accounting.assets.proceeds")}</span>
                <input className="latin" inputMode="decimal" value={proceeds} onChange={(e) => setProceeds(e.target.value)} required />
              </label>
              <button className="btn btn--danger" type="submit">
                {t("accounting.assets.dispose")}
              </button>
              {formError && <p className="error-text">{formError}</p>}
            </form>
          )}
        </>
      )}
    </section>
  );
}
