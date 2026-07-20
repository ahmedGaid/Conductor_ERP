import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Badge, type BadgeTone } from "../../components/Badge";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { getMe } from "../../api/identity";
import {
  createWebhookSubscription,
  deleteWebhookSubscription,
  listWebhookDeliveries,
  listWebhookEvents,
  listWebhookSubscriptions,
  regenerateWebhookSecret,
  retryWebhookDelivery,
  updateWebhookSubscription,
  type WebhookDelivery,
  type WebhookSubscription,
} from "../../api/webhooks";
import { useToast } from "../../app/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { runOptimistic } from "../../lib/optimistic";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import { Toggle } from "./controls";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "../admin/admin.css";

/** Per-subscription delivery tally the Live help tab reads (has anything landed? has any failed?). */
type DeliveryStats = { count: number; failed: number };

const DELIVERY_TONE: Record<WebhookDelivery["status"], BadgeTone> = {
  pending: "pending",
  delivered: "completed",
  retrying: "waiting",
  failed: "failed",
};

let tempSeq = 0;

/** Translated label for a catalog event name ("sales.QuotationConverted"), falling back to the
 *  raw name if a module/event pair hasn't been added to the event.* dictionary yet. */
function eventLabel(t: ReturnType<typeof useTranslation>["t"], name: string): string {
  const key = `settings.webhooks.event.${name}`;
  const label = t(key);
  return label === key ? name : label;
}

/** Splits the flat, alphabetically-sorted event catalog into contiguous per-module groups
 *  ("sales.QuotationConverted" → module "sales") — the sort already keeps each module's events
 *  together, so this only needs to detect where the prefix changes. */
function groupEventsByModule(names: string[]): Array<{ module: string; names: string[] }> {
  const groups: Array<{ module: string; names: string[] }> = [];
  for (const name of names) {
    const [module] = name.split(".");
    const last = groups[groups.length - 1];
    if (last && last.module === module) last.names.push(name);
    else groups.push({ module, names: [name] });
  }
  return groups;
}

function DeliveriesPanel({
  subscriptionId,
  onStats,
}: {
  subscriptionId: string;
  onStats: (id: string, stats: DeliveryStats) => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, errorStatus, reload, mutate } = useAsync(
    () => listWebhookDeliveries(subscriptionId),
    [subscriptionId],
  );

  // Report this subscription's delivery tally up so the Live help tab can tick "a delivery landed"
  // and surface the "a delivery failed" alert — the page only learns delivery state once opened.
  useEffect(() => {
    if (data) {
      onStats(subscriptionId, {
        count: data.length,
        failed: data.filter((d) => d.status === "failed").length,
      });
    }
  }, [data, subscriptionId, onStats]);

  if (loading) return <ListSkeleton />;
  if (error) return <ErrorState message={error} onRetry={reload} status={errorStatus} />;
  if (!data || data.length === 0) {
    return <p className="setrow__desc">{t("settings.webhooks.deliveries.empty")}</p>;
  }

  function retry(delivery: WebhookDelivery) {
    void runOptimistic<WebhookDelivery[], WebhookDelivery>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows,
      request: () => retryWebhookDelivery(delivery.id),
      settle: (rows, updated) => rows.map((r) => (r.id === updated.id ? updated : r)),
      toast,
      success: t("settings.webhooks.deliveries.toastRetried"),
    });
  }

  return (
    <table className="admin-table">
      <thead>
        <tr>
          <th>{t("settings.webhooks.deliveries.event")}</th>
          <th>{t("settings.webhooks.deliveries.status")}</th>
          <th>{t("settings.webhooks.deliveries.attempts")}</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {data.map((d) => (
          <tr key={d.id} className="admin-row">
            <td>{eventLabel(t, d.event_name)}</td>
            <td>
              <Badge tone={DELIVERY_TONE[d.status]}>
                {t(`settings.webhooks.deliveries.status_${d.status}`)}
              </Badge>
            </td>
            <td>{d.attempts}</td>
            <td>
              {(d.status === "retrying" || d.status === "failed") && (
                <button className="btn btn--ghost" type="button" onClick={() => retry(d)}>
                  {t("settings.webhooks.deliveries.retryNow")}
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function WebhooksSettingsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data: me } = useAsync(getMe, []);
  const { data: catalog } = useAsync(listWebhookEvents, [], "settings:webhookEvents");
  const { data, loading, error, errorStatus, reload, mutate } = useAsync(
    listWebhookSubscriptions,
    [],
    "settings:webhooks",
  );

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);
  // Once a secret has been shown this session, the checklist's "copy the secret" step stays ticked
  // even after the reveal card is dismissed — the act happened, don't un-tick it.
  const [secretEverShown, setSecretEverShown] = useState(false);
  const [deliveryStats, setDeliveryStats] = useState<Record<string, DeliveryStats>>({});
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  const reportStats = useCallback((id: string, stats: DeliveryStats) => {
    setDeliveryStats((prev) =>
      prev[id]?.count === stats.count && prev[id]?.failed === stats.failed
        ? prev
        : { ...prev, [id]: stats },
    );
  }, []);

  // Publish the page's live facts for the Help drawer's Live tab (alerts + self-ticking checklist).
  // urlTyped/eventsPicked let the checklist tick as the user fills the form, before they even click
  // Add — the "leading by the hand" bit-by-bit feel.
  useSetHelpSignals({
    subCount: data?.length ?? 0,
    urlTyped: url.trim().length > 0,
    eventsPicked: selectedEvents.length > 0,
    secretJustShown: revealedSecret !== null,
    secretEverShown,
    hasDelivery: Object.values(deliveryStats).some((s) => s.count > 0),
    hasFailedDelivery: Object.values(deliveryStats).some((s) => s.failed > 0),
  });

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.webhooks.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!me || loading) return <SettingsSkeleton />;

  function toggleEvent(name: string) {
    setSelectedEvents((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || selectedEvents.length === 0) return;
    const tempId = `tmp-${++tempSeq}`;
    const events = selectedEvents;
    const created = await runOptimistic<WebhookSubscription[], WebhookSubscription>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => [
        { id: tempId, url: trimmed, event_names: events, is_active: true,
          created_at: new Date().toISOString() },
        ...rows,
      ],
      request: () => createWebhookSubscription({ url: trimmed, event_names: events }),
      settle: (rows, result) => rows.map((r) => (r.id === tempId ? result : r)),
      toast,
      success: t("settings.webhooks.toastCreated"),
    });
    if (created) {
      setRevealedSecret((created as WebhookSubscription & { secret: string }).secret);
      setSecretEverShown(true);
      setUrl("");
      setSelectedEvents([]);
    }
  }

  function toggleActive(sub: WebhookSubscription) {
    const next = !sub.is_active;
    void runOptimistic<WebhookSubscription[], WebhookSubscription>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((s) => (s.id === sub.id ? { ...s, is_active: next } : s)),
      request: () => updateWebhookSubscription(sub.id, { is_active: next }),
      settle: (rows, updated) => rows.map((s) => (s.id === updated.id ? updated : s)),
      toast,
      success: t("settings.webhooks.toastUpdated"),
    });
  }

  async function regenerate(sub: WebhookSubscription) {
    try {
      const updated = await regenerateWebhookSecret(sub.id);
      setRevealedSecret(updated.secret);
      setSecretEverShown(true);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  function remove(sub: WebhookSubscription) {
    void runOptimistic<WebhookSubscription[], void>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.filter((s) => s.id !== sub.id),
      request: () => deleteWebhookSubscription(sub.id),
      toast,
      success: t("settings.webhooks.toastDeleted"),
    });
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <p className="setrow__desc setcard__lead">{t("settings.webhooks.lead")}</p>

      {revealedSecret && (
        <div className="card setcard" role="status">
          <p className="setrow__title">{t("settings.webhooks.secretRevealTitle")}</p>
          <p className="setrow__desc">{t("settings.webhooks.secretRevealDesc")}</p>
          <code className="latin webhook-secret">{revealedSecret}</code>
          <div className="admin-invite__foot">
            <button className="btn btn--ghost" type="button" onClick={() => setRevealedSecret(null)}>
              {t("settings.webhooks.secretRevealDismiss")}
            </button>
          </div>
        </div>
      )}

      <form ref={formRef} className="card admin-invite" onSubmit={(e) => void onSubmit(e)}>
        <div className="admin-invite__grid">
          <label className="admin-field">
            <span>{t("settings.webhooks.url")}</span>
            <input
              className="latin"
              type="url"
              placeholder="https://example.com/webhook"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
          </label>
        </div>
        <div className="admin-field">
          <span>{t("settings.webhooks.events")}</span>
          <div className="webhook-events">
            {groupEventsByModule(catalog ?? []).map((group) => (
              <fieldset key={group.module} className="webhook-events__group">
                <legend>{t(`nav.${group.module}`, group.module)}</legend>
                {group.names.map((name) => (
                  <label key={name} className="webhook-event-label">
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(name)}
                      onChange={() => toggleEvent(name)}
                    />
                    {eventLabel(t, name)}
                  </label>
                ))}
              </fieldset>
            ))}
          </div>
        </div>
        <div className="admin-invite__foot">
          <button className="btn btn--primary" type="submit" disabled={selectedEvents.length === 0}>
            {t("settings.webhooks.add")}
          </button>
        </div>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} status={errorStatus} />}

      {data && data.length === 0 && (
        <EmptyState title={t("settings.webhooks.empty")} hint={t("settings.webhooks.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("settings.webhooks.url")}</th>
                <th>{t("settings.webhooks.events")}</th>
                <th>{t("settings.webhooks.active")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((sub) => (
                <Fragment key={sub.id}>
                  <tr className="admin-row">
                    <td className="latin">{sub.url}</td>
                    <td>{sub.event_names.map((n) => eventLabel(t, n)).join(", ")}</td>
                    <td>
                      <Toggle
                        checked={sub.is_active}
                        onChange={() => toggleActive(sub)}
                        label={t("settings.webhooks.active")}
                      />
                    </td>
                    <td className="webhook-row-actions">
                      <button
                        className="btn btn--ghost"
                        type="button"
                        onClick={() => setExpanded(expanded === sub.id ? null : sub.id)}
                      >
                        {t("settings.webhooks.deliveries.title")}
                      </button>
                      <button className="btn btn--ghost" type="button" onClick={() => void regenerate(sub)}>
                        {t("settings.webhooks.regenerateSecret")}
                      </button>
                      <button className="btn btn--ghost" type="button" onClick={() => remove(sub)}>
                        {t("settings.webhooks.delete")}
                      </button>
                    </td>
                  </tr>
                  {expanded === sub.id && (
                    <tr>
                      <td colSpan={4}>
                        <DeliveriesPanel subscriptionId={sub.id} onStats={reportStats} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
