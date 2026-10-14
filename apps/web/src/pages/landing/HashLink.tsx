import type { AnchorHTMLAttributes, MouseEvent, ReactNode } from "react";

/**
 * In-page anchor for the landing page. The app runs under HashRouter, so a real `#id` href would
 * be swallowed by the router as a route change — instead we scroll to the target element by id in
 * JS (honouring reduced-motion). `to` is like "#pricing"; the leading # is the element id.
 */
interface HashLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to: string;
  children: ReactNode;
}

export function HashLink({ to, children, onClick, ...rest }: HashLinkProps) {
  const id = to.replace(/^#/, "");

  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented) return;
    const el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    // Move keyboard focus to the target so the jump is accessible, without a focus ring flash.
    el.setAttribute("tabindex", "-1");
    (el as HTMLElement).focus({ preventScroll: true });
  };

  return (
    <a href={to} onClick={handle} {...rest}>
      {children}
    </a>
  );
}
