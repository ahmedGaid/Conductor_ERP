// Typed wrappers for the notifications API (/api/notifications). The delivery log + resend.
import { apiFetch } from "./client";

export type NotificationChannel = "email" | "whatsapp" | "inapp";
export type NotificationStatus = "pending" | "sent" | "failed";

export interface Notification {
  id: string;
  channel: NotificationChannel;
  recipient: string;
  subject: string;
  body: string;
  reference: string;
  event_name: string;
  status: NotificationStatus;
  provider_ref: string;
  error_text: string;
  sent_at: string | null;
  created_at: string;
}

export function listNotifications(params?: {
  channel?: NotificationChannel;
  status?: NotificationStatus;
}): Promise<Notification[]> {
  const qs = new URLSearchParams();
  if (params?.channel) qs.set("channel", params.channel);
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiFetch<Notification[]>(`/notifications${suffix}`);
}

export function resendNotification(id: string): Promise<Notification> {
  return apiFetch<Notification>(`/notifications/${id}/resend`, { method: "POST", body: "{}" });
}

// --- In-app inbox: the signed-in user's own notifications (unread first) ---

export interface InboxItem {
  id: string;
  subject: string;
  body: string;
  reference: string;
  event_name: string;
  read_at: string | null;
  created_at: string;
}

export function listInbox(): Promise<InboxItem[]> {
  return apiFetch<InboxItem[]>(`/notifications/inbox`);
}

export function markInboxRead(id: string): Promise<InboxItem> {
  return apiFetch<InboxItem>(`/notifications/inbox/${id}/read`, { method: "POST", body: "{}" });
}

export function markAllInboxRead(): Promise<{ count: number }> {
  return apiFetch<{ count: number }>(`/notifications/inbox/read-all`, { method: "POST", body: "{}" });
}
