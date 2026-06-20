import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import i18n from "../i18n";

import { getEffectivePreferences, patchPreferences, type Preferences } from "../api/identity";
import { applyPreferences } from "../prefs";

interface PreferencesState {
  prefs: Preferences | null;
  loading: boolean;
  /** Optimistically apply + persist a partial change to the signed-in user's preferences. */
  update: (changes: Partial<Preferences>) => Promise<void>;
}

const PreferencesContext = createContext<PreferencesState | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount (already authenticated), pull the effective preferences (org defaults ⊕ personal),
  // apply them to <html>, and sync the UI language.
  useEffect(() => {
    let alive = true;
    getEffectivePreferences()
      .then((p) => {
        if (!alive) return;
        setPrefs(p);
        applyPreferences(p);
        if (p.preferred_language && p.preferred_language !== i18n.resolvedLanguage) {
          i18n.changeLanguage(p.preferred_language);
        }
      })
      .catch(() => {
        /* a missing/failed prefs fetch must never block the app — defaults already applied */
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  async function update(changes: Partial<Preferences>) {
    // Optimistic: reflect immediately, then persist. On failure, reload truth from the server.
    setPrefs((cur) => (cur ? { ...cur, ...changes } : cur));
    applyPreferences(changes);
    if (changes.preferred_language) i18n.changeLanguage(changes.preferred_language);
    try {
      const saved = await patchPreferences(changes);
      setPrefs(saved);
    } catch {
      const fresh = await getEffectivePreferences().catch(() => null);
      if (fresh) {
        setPrefs(fresh);
        applyPreferences(fresh);
      }
    }
  }

  return (
    <PreferencesContext.Provider value={{ prefs, loading, update }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesState {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferences must be used within PreferencesProvider");
  return ctx;
}
