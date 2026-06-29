import type { ReactNode } from "react";

import { NavIcon } from "../app/icons";
import "./documentDetail.css";

export type StatusTone = "done" | "active" | "exception";

const TONE_ICON: Record<StatusTone, string> = {
  done: "checkCircle",
  active: "info",
  exception: "rotate",
};

/**
 * Plain-language state line under the document header: an icon + a headline and an optional detail
 * ("Paid in full — nothing more to do. / All steps completed on …"). Colour is carried by the icon
 * only and always pairs with the words — `done` reads success, `exception` reads danger, `active`
 * stays neutral.
 */
export function DocumentStatusNote({
  tone,
  title,
  detail,
}: {
  tone: StatusTone;
  title: ReactNode;
  detail?: ReactNode;
}) {
  return (
    <div className={`docnote docnote--${tone}`}>
      <span className="docnote__icon" aria-hidden="true">
        <NavIcon name={TONE_ICON[tone]} />
      </span>
      <div className="docnote__text">
        <p className="docnote__title">{title}</p>
        {detail && <p className="docnote__detail">{detail}</p>}
      </div>
    </div>
  );
}
