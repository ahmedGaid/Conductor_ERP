import { useCallback, useEffect, useState } from "react";

import {
  listInbox,
  markAllInboxRead,
  markInboxRead,
  type InboxItem,
} from "../api/notifications";

/**
 * The in-app inbox state, loaded once on mount so the bell's unread dot is correct before the panel
 * is ever opened. Marking read is optimistic — the row reads as read at once and the server call is
 * best-effort (a failed mark leaves a harmless stale dot, never blocks the UI). Reads are the user's
 * own rows only (the API isolates by user).
 */
export function useInbox() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listInbox());
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const markRead = useCallback((id: string) => {
    const now = new Date().toISOString();
    setItems((cur) => cur.map((n) => (n.id === id ? { ...n, read_at: n.read_at ?? now } : n)));
    void markInboxRead(id).catch(() => {
      /* best-effort — the row already reads as read locally */
    });
  }, []);

  const markAll = useCallback(() => {
    const now = new Date().toISOString();
    setItems((cur) => cur.map((n) => (n.read_at ? n : { ...n, read_at: now })));
    void markAllInboxRead().catch(() => {
      /* best-effort */
    });
  }, []);

  const unread = items.some((n) => n.read_at === null);
  return { items, unread, loading, error, reload, markRead, markAll };
}
