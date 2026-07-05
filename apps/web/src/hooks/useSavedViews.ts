import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import {
  createSavedView,
  deleteSavedView,
  listSavedViews,
  renameSavedView,
  setDefaultSavedView,
  type SavedView,
} from "../api/savedViews";
import { useToast } from "../app/ToastContext";
import {
  canonicalizeQuery,
  filtersFromParams,
  paramsFromFilters,
  type ActiveFilter,
  type FilterField,
} from "../lib/filters";

interface Options<T> {
  /** Stable list identity, e.g. "sales:orders" — the presets are scoped to it. */
  listKey: string;
  fields: FilterField<T>[];
  /** The page's live filter chips (owned by the page, so editing keeps stable chip ids). */
  filters: ActiveFilter[];
  setFilters: (filters: ActiveFilter[]) => void;
}

export interface SavedViewsApi {
  views: SavedView[];
  activeView: SavedView | null;
  /** True when the current filters are worth saving (non-empty and not already a saved view). */
  canSave: boolean;
  /** Apply a view (or `null` for the unfiltered "All"); pushes history so Back returns here. */
  applyView: (view: SavedView | null) => void;
  saveView: (name: string) => void;
  renameView: (view: SavedView, name: string) => void;
  deleteView: (view: SavedView) => void;
  setDefaultView: (view: SavedView) => void;
}

/**
 * The controller behind <SavedViews>: keeps the URL query in step with the page's filter chips,
 * loads the user's presets for this list, and applies the default one on a fresh visit.
 *
 * The chips stay the page's own state (so typing never rebuilds them); this hook only mirrors them
 * to the URL (replace, no history spam) and adopts external URL changes — Back/Forward and view
 * switches (which push) — back into the chips. Both directions are guarded by a canonical compare,
 * so the two effects can never ping-pong.
 */
export function useSavedViews<T>({ listKey, fields, filters, setFilters }: Options<T>): SavedViewsApi {
  const { t } = useTranslation();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [views, setViews] = useState<SavedView[]>([]);
  const [loaded, setLoaded] = useState(false);
  const appliedDefault = useRef(false);

  const currentQuery = useMemo(() => paramsFromFilters(filters).toString(), [filters]);
  const urlQuery = searchParams.toString();

  // Load this list's presets once.
  useEffect(() => {
    let alive = true;
    listSavedViews(listKey)
      .then((vs) => alive && setViews(vs))
      .catch(() => {
        /* views are a convenience — a load failure just leaves the control empty, never blocks the list */
      })
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
    };
  }, [listKey]);

  // Chips → URL. Replace so editing filters never floods history; deep-links / view switches come
  // back the other way (below). Runs only when the chips actually change (dep: currentQuery).
  useEffect(() => {
    if (canonicalizeQuery(urlQuery) !== canonicalizeQuery(currentQuery)) {
      setSearchParams(paramsFromFilters(filters), { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentQuery]);

  // URL → chips. Back/Forward and view switches (which push a new query) land here. Guarded so our
  // own replace-writes above don't loop; only a genuinely different URL rebuilds the chips.
  useEffect(() => {
    if (canonicalizeQuery(urlQuery) !== canonicalizeQuery(currentQuery)) {
      setFilters(filtersFromParams(new URLSearchParams(urlQuery), fields));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlQuery]);

  const applyView = useCallback(
    (view: SavedView | null) => {
      appliedDefault.current = true; // an explicit choice (incl. "All") ends default auto-apply
      setSearchParams(new URLSearchParams(view ? view.query : ""), { replace: false });
    },
    [setSearchParams],
  );

  // Apply the default view on a fresh visit (no filters yet). A deep-link or an in-progress edit
  // wins — we only auto-apply when arriving clean, and only once.
  useEffect(() => {
    if (!loaded || appliedDefault.current) return;
    appliedDefault.current = true;
    if (currentQuery === "") {
      const def = views.find((v) => v.is_default && v.query);
      if (def) applyView(def);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded]);

  const activeView = useMemo(
    () => views.find((v) => canonicalizeQuery(v.query) === canonicalizeQuery(currentQuery)) ?? null,
    [views, currentQuery],
  );
  const canSave = currentQuery !== "" && !activeView;

  const byName = (a: SavedView, b: SavedView) => a.name.localeCompare(b.name);

  const saveView = useCallback(
    async (name: string) => {
      try {
        const created = await createSavedView({ list_key: listKey, name, query: currentQuery });
        setViews((vs) => [...vs, created].sort(byName));
        toast.show(t("views.toast.saved"), "success");
      } catch (e) {
        toast.show(e instanceof Error ? e.message : String(e), "error");
      }
    },
    [listKey, currentQuery, toast, t],
  );

  const renameView = useCallback(
    async (view: SavedView, name: string) => {
      try {
        const updated = await renameSavedView(view.id, name);
        setViews((vs) => vs.map((v) => (v.id === updated.id ? updated : v)).sort(byName));
        toast.show(t("views.toast.renamed"), "success");
      } catch (e) {
        toast.show(e instanceof Error ? e.message : String(e), "error");
      }
    },
    [toast, t],
  );

  const deleteView = useCallback(
    async (view: SavedView) => {
      try {
        await deleteSavedView(view.id);
        setViews((vs) => vs.filter((v) => v.id !== view.id));
        toast.show(t("views.toast.deleted"), "success");
      } catch (e) {
        toast.show(e instanceof Error ? e.message : String(e), "error");
      }
    },
    [toast, t],
  );

  const setDefaultView = useCallback(
    async (view: SavedView) => {
      try {
        const updated = await setDefaultSavedView(view.id);
        // One default per list — reflect that locally too.
        setViews((vs) => vs.map((v) => ({ ...v, is_default: v.id === updated.id })));
        toast.show(t("views.toast.defaultSet"), "success");
      } catch (e) {
        toast.show(e instanceof Error ? e.message : String(e), "error");
      }
    },
    [toast, t],
  );

  return { views, activeView, canSave, applyView, saveView, renameView, deleteView, setDefaultView };
}
