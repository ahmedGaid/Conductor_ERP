import { useEffect, useRef, useState } from "react";

/**
 * Returns [ref, inView] — `inView` flips true once (and stays true) when the element first enters
 * the viewport. One-shot, so entrance-driven effects (count-ups, choreography) fire a single time.
 * Falls back to `true` where IntersectionObserver is unavailable so content never stays hidden.
 */
export function useInView<T extends HTMLElement = HTMLDivElement>(rootMargin = "0px 0px -15% 0px") {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { rootMargin, threshold: 0.2 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [rootMargin]);

  return [ref, inView] as const;
}
