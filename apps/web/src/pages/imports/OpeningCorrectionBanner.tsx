import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { Bdi } from "../../components/Bdi";
import { formatMinor } from "../../lib/money";
import type { ImportStats } from "../../api/smartImports";

// Renders when AccountOpeningAdapter.validate_group finds the trial balance doesn't balance
// (batch.stats.opening_correction). Every row stays `error` until a human approves the suggested
// suspense-account line here — the engine never forces a balance on its own (FILE_17 acceptance).
export function OpeningCorrectionBanner({
  correction,
  approving,
  onApprove,
}: {
  correction: NonNullable<ImportStats["opening_correction"]>;
  approving: boolean;
  onApprove: () => void;
}) {
  const { t } = useTranslation();
  const { proposed_line: line } = correction;
  const side = line.credit_minor > 0 ? "sideCredit" : "sideDebit";
  const sideAmount = line.credit_minor > 0 ? line.credit_minor : line.debit_minor;

  return (
    <section className="imports-opening-correction card">
      <header className="imports-opening-correction__head">
        <NavIcon name="warning" />
        <div>
          <h2 className="imports-opening-correction__title">{t("imports.openingCorrection.title")}</h2>
          <p className="imports-opening-correction__hint">
            {t("imports.openingCorrection.hint", { amount: formatMinor(Math.abs(correction.difference_minor)) })}
          </p>
        </div>
      </header>

      <dl className="imports-opening-correction__figures">
        <div>
          <dt className="muted">{t("imports.openingCorrection.totalDebit")}</dt>
          <dd><Bdi>{formatMinor(correction.total_debit_minor)}</Bdi></dd>
        </div>
        <div>
          <dt className="muted">{t("imports.openingCorrection.totalCredit")}</dt>
          <dd><Bdi>{formatMinor(correction.total_credit_minor)}</Bdi></dd>
        </div>
        <div>
          <dt className="muted">{t("imports.openingCorrection.difference")}</dt>
          <dd><Bdi>{formatMinor(Math.abs(correction.difference_minor))}</Bdi></dd>
        </div>
      </dl>

      <p className="imports-opening-correction__suggestion muted">
        <Bdi>
          {t("imports.openingCorrection.suggestedLine", {
            account: correction.suspense_account,
            side: t(`imports.openingCorrection.${side}`),
            amount: formatMinor(sideAmount),
          })}
        </Bdi>
      </p>

      <footer className="imports-opening-correction__foot">
        {correction.approved ? (
          <span className="imports-opening-correction__done muted">
            <NavIcon name="check" />
            {t("imports.openingCorrection.approved")}
          </span>
        ) : (
          <button type="button" className="btn btn--primary" disabled={approving} onClick={onApprove}>
            {approving ? t("common.loading") : t("imports.openingCorrection.approve")}
          </button>
        )}
      </footer>
    </section>
  );
}
