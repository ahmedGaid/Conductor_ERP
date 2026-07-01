import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createPriceList, listPriceLists, type PriceList } from "../../api/pricing";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { Bdi } from "../../components/Bdi";
import { PricingTabs } from "./PricingTabs";
import "./pricing.css";

export function PriceListsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listPriceLists, [], "pricing:lists");

  // j/k move a row highlight, Enter/o opens the price-list detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<PriceList>({
    items: data ?? [],
    onOpen: (pl) => navigate(`/pricing/${pl.id}`),
    persistKey: "pricing:lists",
    getItemId: (pl) => pl.id,
  });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("EGP");
  const [taxInclusive, setTaxInclusive] = useState(false);
  const [isDefault, setIsDefault] = useState(false);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    const makeDefault = isDefault;
    void optimisticCreate<PriceList>({
      current: data ?? [],
      mutate,
      placeholder: (id) =>
        ({
          id, code: c, name: n, currency: currency.trim() || "EGP",
          tax_inclusive: taxInclusive, is_default: makeDefault, is_active: true, line_count: 0,
        }) as PriceList,
      request: () =>
        createPriceList({ code: c, name: n, currency: currency.trim() || "EGP", tax_inclusive: taxInclusive, is_default: makeDefault }),
      toast,
      success: t("pricing.toast.listCreated"),
    });
    setCode("");
    setName("");
    setTaxInclusive(false);
    setIsDefault(false);
  }

  return (
    <section className="pricing-page">
      <div className="pricing-head">
        <h1>{t("pricing.title")}</h1>
        <p className="muted">{t("pricing.subtitle")}</p>
      </div>

      <PricingTabs active="lists" />

      <form className="card pricing-toolbar" onSubmit={onSubmit}>
        <label className="pricing-field">
          <span>{t("pricing.list.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.list.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.list.currency")}</span>
          <input className="latin" value={currency} onChange={(e) => setCurrency(e.target.value)} maxLength={3} />
        </label>
        <label className="pricing-field pricing-field--check">
          <input type="checkbox" checked={taxInclusive} onChange={(e) => setTaxInclusive(e.target.checked)} />
          <span>{t("pricing.list.taxInclusive")}</span>
        </label>
        <label className="pricing-field pricing-field--check">
          <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
          <span>{t("pricing.list.default")}</span>
        </label>
        <button className="btn btn--primary" type="submit">
          {t("pricing.list.add")}
        </button>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("pricing.list.empty")} hint={t("pricing.list.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card pricing-table-wrap">
          <table className="pricing-table">
            <thead>
              <tr>
                <th>{t("pricing.list.code")}</th>
                <th>{t("pricing.list.name")}</th>
                <th>{t("pricing.list.currency")}</th>
                <th className="pricing-table__num">{t("pricing.list.lines")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((pl, i) => (
                <tr key={pl.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <Link to={`/pricing/${pl.id}`} className="inv-link">
                      <Bdi>{pl.code}</Bdi>
                    </Link>
                  </td>
                  <td>{pl.name}</td>
                  <td><Bdi>{pl.currency}</Bdi></td>
                  <td className="pricing-table__num"><Bdi>{pl.line_count}</Bdi></td>
                  <td>
                    {pl.is_default && <span className="pricing-tag">{t("pricing.list.default")}</span>}
                    {pl.tax_inclusive && <span className="pricing-tag">{t("pricing.list.taxInclusive")}</span>}
                    {!pl.is_active && <span className="pricing-tag">{t("pricing.list.inactive")}</span>}
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
