import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createItem, listItems, type ItemType } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

export function ItemsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listItems, [], "inventory:items");

  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [uom, setUom] = useState("unit");
  const [type, setType] = useState<ItemType>("stock");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createItem({ sku, name, uom, type });
      setSku("");
      setName("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <h1>{t("nav.inventory")}</h1>
      <InventoryNav />

      <form className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.item.sku")}</span>
          <input className="latin" value={sku} onChange={(e) => setSku(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.uom")}</span>
          <input value={uom} onChange={(e) => setUom(e.target.value)} />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.type")}</span>
          <select value={type} onChange={(e) => setType(e.target.value as ItemType)}>
            <option value="stock">{t("inventory.types.stock")}</option>
            <option value="service">{t("inventory.types.service")}</option>
          </select>
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("inventory.item.add")}
        </button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.item.sku")}</th>
                <th>{t("inventory.item.name")}</th>
                <th>{t("inventory.item.uom")}</th>
                <th>{t("inventory.item.type")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((i) => (
                <tr key={i.id}>
                  <td><Bdi>{i.sku}</Bdi></td>
                  <td>{i.name}</td>
                  <td>{i.uom}</td>
                  <td>{t(`inventory.types.${i.type}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
