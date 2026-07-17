// Typed wrappers for the outbound-webhooks API (/api/notifications/webhooks). Admin-only.
import { apiFetch } from "./client";

export interface WebhookSubscription {
  id: string;
  url: string;
  event_names: string[];
  is_active: boolean;
  created_at: string;
}

export interface WebhookSubscriptionWithSecret extends WebhookSubscription {
  secret: string;
}

export type WebhookDeliveryStatus = "pending" | "delivered" | "retrying" | "failed";

export interface WebhookDelivery {
  id: string;
  event_name: string;
  status: WebhookDeliveryStatus;
  attempts: number;
  last_error: string;
  next_retry_at: string | null;
  created_at: string;
}

export function listWebhookEvents(): Promise<string[]> {
  return apiFetch<string[]>("/notifications/webhooks/events");
}

export function listWebhookSubscriptions(): Promise<WebhookSubscription[]> {
  return apiFetch<WebhookSubscription[]>("/notifications/webhooks");
}

export function createWebhookSubscription(payload: {
  url: string;
  event_names: string[];
}): Promise<WebhookSubscriptionWithSecret> {
  return apiFetch<WebhookSubscriptionWithSecret>("/notifications/webhooks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWebhookSubscription(
  id: string,
  changes: Partial<{ url: string; event_names: string[]; is_active: boolean }>,
): Promise<WebhookSubscription> {
  return apiFetch<WebhookSubscription>(`/notifications/webhooks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function deleteWebhookSubscription(id: string): Promise<void> {
  return apiFetch<void>(`/notifications/webhooks/${id}`, { method: "DELETE" });
}

export function regenerateWebhookSecret(id: string): Promise<WebhookSubscriptionWithSecret> {
  return apiFetch<WebhookSubscriptionWithSecret>(`/notifications/webhooks/${id}/secret`, {
    method: "POST",
    body: "{}",
  });
}

export function listWebhookDeliveries(id: string): Promise<WebhookDelivery[]> {
  return apiFetch<WebhookDelivery[]>(`/notifications/webhooks/${id}/deliveries`);
}

export function retryWebhookDelivery(deliveryId: string): Promise<WebhookDelivery> {
  return apiFetch<WebhookDelivery>(`/notifications/webhooks/deliveries/${deliveryId}/retry`, {
    method: "POST",
    body: "{}",
  });
}
