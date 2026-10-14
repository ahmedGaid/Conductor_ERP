import { useEffect, useRef, useState } from "react";

const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Counts up to `value` when `active` becomes true — the product frame's figures animate to life the
 * first time the hero settles into view. Reduced-motion (or no `active`) shows the final value at
 * once. Grouped with Latin digits in both locales (brand rule). `prefix`/`suffix` render verbatim.
 */
export function AnimatedNumber({
  value,
  active,
  duration = 1100,
  prefix = "",
  suffix = "",
}: {
  value: number;
  active: boolean;
  duration?: number;
  prefix?: string;
  suffix?: string;
}) {
  const [display, setDisplay] = useState(() => (active && !prefersReduced() ? 0 : value));
  const started = useRef(false);

  useEffect(() => {
    if (!active || started.current) return;
    started.current = true;
    if (prefersReduced()) {
      setDisplay(value);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration);
      // ease-out-quart — decisive, no overshoot.
      const e = 1 - Math.pow(1 - p, 4);
      setDisplay(value * e);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, value, duration]);

  return (
    <span className="num">
      {prefix}
      {Math.round(display).toLocaleString("en-US")}
      {suffix}
    </span>
  );
}
