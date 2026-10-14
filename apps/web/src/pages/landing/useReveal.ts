import { useEffect, useRef } from "react";

/**
 * Reveal-on-scroll: attach the returned ref to a section; it gains the `is-in` class the first
 * time it scrolls into view (one-shot, then unobserved). The CSS carries the actual motion and
 * respects reduced-motion, so when motion is off the element simply starts visible.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // No IO (SSR/old browsers) → show immediately, never leave content hidden.
    if (typeof IntersectionObserver === "undefined") {
      el.classList.add("is-in");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return ref;
}
