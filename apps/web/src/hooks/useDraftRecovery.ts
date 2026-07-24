import { useCallback, useEffect, useRef, useState } from "react";

import {
  completeDraft,
  discardDraft,
  flushDraft,
  getActiveDraft,
  saveDraft,
  type DraftSaveBody,
} from "../api/workSessions";
import { hasConflict, isMeaningfulChange, reconcile } from "../lib/draftRecovery";

const IDLE_MS = 800;
const MAX_WAIT_MS = 5000;

function localKey(workflowKey: string, relatedEntityId: string): string {
  return `erp.draft.${workflowKey}.${relatedEntityId}`;
}

interface LocalMirror<T> {
  payload: T;
  clientVersion: number;
  savedAt: number;
}

export interface DraftRecovery<T> {
  status: "idle" | "saving" | "saved";
  savedAt: Date | null;
  recoverable: { payload: T; lastActiveAt: string } | null;
  /** Apply the offered draft: returns its payload for the page to load, and clears the banner. */
  recover: () => T | null;
  discard: () => Promise<void>;
  complete: (relatedEntityId?: string) => Promise<void>;
  conflict: boolean;
}

export function useDraftRecovery<T>(opts: {
  workflowKey: string;
  value: T;
  baseline: T;
  schemaVersion: number;
  relatedEntityId?: string;
  entityType?: string;
  enabled?: boolean;
}): DraftRecovery<T> {
  const {
    workflowKey,
    value,
    baseline,
    schemaVersion,
    relatedEntityId = "",
    entityType = "",
    enabled = true,
  } = opts;

  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [recoverable, setRecoverable] = useState<{ payload: T; lastActiveAt: string } | null>(null);
  const [conflict, setConflict] = useState(false);

  // Bookkeeping in refs so the debounce/flush closures always read the latest.
  const sessionIdRef = useRef<string | null>(null);
  const serverVersionRef = useRef(0);
  const lastSavedJsonRef = useRef<string | null>(null);
  const valueRef = useRef(value);
  valueRef.current = value;

  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const lsKey = localKey(workflowKey, relatedEntityId);

  function writeMirror(payload: T, clientVersion: number) {
    try {
      localStorage.setItem(lsKey, JSON.stringify({ payload, clientVersion, savedAt: Date.now() }));
    } catch {
      /* storage unavailable (private mode) */
    }
  }

  // --- mount: fetch the active draft, reconcile with the local mirror, offer recovery ---
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let local: LocalMirror<T> | null = null;
    try {
      const raw = localStorage.getItem(lsKey);
      if (raw) local = JSON.parse(raw) as LocalMirror<T>;
    } catch {
      /* ignore */
    }

    getActiveDraft(workflowKey, relatedEntityId)
      .then((server) => {
        if (cancelled) return;
        if (server) {
          sessionIdRef.current = server.id;
          serverVersionRef.current = server.client_version;
        }
        const chosen = reconcile(
          server ? { payload: server.payload as T, clientVersion: server.client_version } : null,
          local ? { payload: local.payload, clientVersion: local.clientVersion } : null,
        );
        if (chosen.source !== "none" && chosen.payload != null && isMeaningfulChange(chosen.payload, baseline)) {
          const lastActiveAt = server?.last_active_at ?? new Date(local?.savedAt ?? Date.now()).toISOString();
          setRecoverable({ payload: chosen.payload, lastActiveAt });
        }
      })
      .catch(() => {
        // Offline: fall back to the local mirror only.
        if (cancelled || !local) return;
        if (isMeaningfulChange(local.payload, baseline)) {
          setRecoverable({ payload: local.payload, lastActiveAt: new Date(local.savedAt).toISOString() });
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, enabled]);

  // --- the actual save ---
  const doSave = useCallback(async () => {
    const current = valueRef.current;
    if (!isMeaningfulChange(current, baseline)) return;
    const json = JSON.stringify(current);
    if (json === lastSavedJsonRef.current) return;
    setStatus("saving");
    const body: DraftSaveBody = {
      workflow_key: workflowKey,
      payload: current,
      entity_type: entityType,
      related_entity_id: relatedEntityId,
      schema_version: schemaVersion,
      client_version: serverVersionRef.current + 1,
      expected_version: serverVersionRef.current,
    };
    try {
      const res = await saveDraft(body);
      if (res.conflict) {
        setConflict(true);
        setStatus("idle");
        return;
      }
      sessionIdRef.current = res.session.id;
      serverVersionRef.current = res.session.client_version;
      lastSavedJsonRef.current = json;
      writeMirror(current, res.session.client_version);
      setSavedAt(new Date());
      setStatus("saved");
    } catch {
      // Network failure: keep the local mirror as the backstop; stay idle so the next edit retries.
      writeMirror(current, serverVersionRef.current + 1);
      setStatus("idle");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, entityType, schemaVersion, baseline, lsKey]);

  // --- debounce: idle 800 ms, max-wait 5 s ---
  useEffect(() => {
    if (!enabled) return;
    if (!isMeaningfulChange(value, baseline)) return;
    if (JSON.stringify(value) === lastSavedJsonRef.current) return;

    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      if (maxTimer.current) {
        clearTimeout(maxTimer.current);
        maxTimer.current = null;
      }
      void doSave();
    }, IDLE_MS);

    if (!maxTimer.current) {
      maxTimer.current = setTimeout(() => {
        if (idleTimer.current) {
          clearTimeout(idleTimer.current);
          idleTimer.current = null;
        }
        maxTimer.current = null;
        void doSave();
      }, MAX_WAIT_MS);
    }

    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, enabled]);

  // --- flush on hide/unload (keepalive fetch carries the bearer header) ---
  useEffect(() => {
    if (!enabled) return;
    function flush() {
      const current = valueRef.current;
      if (!isMeaningfulChange(current, baseline)) return;
      if (JSON.stringify(current) === lastSavedJsonRef.current) return;
      flushDraft({
        workflow_key: workflowKey,
        payload: current,
        entity_type: entityType,
        related_entity_id: relatedEntityId,
        schema_version: schemaVersion,
        client_version: serverVersionRef.current + 1,
        expected_version: serverVersionRef.current,
      });
    }
    function onVisibility() {
      if (document.visibilityState === "hidden") flush();
    }
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, entityType, schemaVersion, enabled]);

  // --- cross-tab: a sibling tab wrote a newer version → conflict ---
  useEffect(() => {
    if (!enabled) return;
    function onStorage(e: StorageEvent) {
      if (e.key !== lsKey || !e.newValue) return;
      try {
        const mirror = JSON.parse(e.newValue) as LocalMirror<T>;
        if (hasConflict(serverVersionRef.current, mirror.clientVersion)) setConflict(true);
      } catch {
        /* ignore */
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lsKey, enabled]);

  const recover = useCallback((): T | null => {
    const payload = recoverable?.payload ?? null;
    setRecoverable(null);
    return payload;
  }, [recoverable]);

  const discard = useCallback(async () => {
    setRecoverable(null);
    lastSavedJsonRef.current = null;
    try {
      localStorage.removeItem(lsKey);
    } catch {
      /* ignore */
    }
    const id = sessionIdRef.current;
    if (id) {
      try {
        await discardDraft(id);
      } catch {
        /* ignore */
      }
    }
    sessionIdRef.current = null;
    serverVersionRef.current = 0;
    setStatus("idle");
    setSavedAt(null);
  }, [lsKey]);

  const complete = useCallback(
    async (rid?: string) => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      if (maxTimer.current) clearTimeout(maxTimer.current);
      try {
        localStorage.removeItem(lsKey);
      } catch {
        /* ignore */
      }
      const id = sessionIdRef.current;
      if (id) {
        try {
          await completeDraft(id, rid ?? relatedEntityId);
        } catch {
          /* ignore */
        }
      }
      sessionIdRef.current = null;
    },
    [lsKey, relatedEntityId],
  );

  return { status, savedAt, recoverable, recover, discard, complete, conflict };
}
