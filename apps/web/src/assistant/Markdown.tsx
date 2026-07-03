import { Fragment, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { Bdi } from "../components/Bdi";

/**
 * A tiny, in-house Markdown renderer — exactly what an AI answer needs and nothing more. No
 * dependency (DECISIONS: no new npm), no `dangerouslySetInnerHTML`: we parse the text and emit React
 * nodes, so React escapes every value for us. Scope: paragraphs, **bold**, *italic*, `inline code`,
 * fenced code blocks, `-`/`1.` lists (one nesting level), `###` headings, GFM tables, and links
 * (internal paths → in-app <Link>, external → new-tab anchor). Prose blocks are `dir="auto"` so an
 * Arabic or English answer lays out correctly; Latin runs (code) carry the `latin` type voice.
 */
export function Markdown({ text, onNavigate }: { text: string; onNavigate?: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();

  const copyCode = (code: string) => {
    navigator.clipboard
      ?.writeText(code)
      .then(() => toast.show(t("assistant.copied"), "success"))
      .catch(() => toast.show(t("assistant.errorLine"), "error"));
  };

  return <div className="assistant-md">{renderBlocks(text, onNavigate, copyCode, t("assistant.copy"))}</div>;
}

// --- inline runs (bold / italic / code / links) ------------------------------------------------
// Find the earliest special token, split around it, recurse on what follows. Code spans win first
// so formatting characters inside them stay literal.
const INLINE = [
  { kind: "code", re: /`([^`]+)`/ },
  { kind: "link", re: /\[([^\]]+)\]\(([^)\s]+)\)/ },
  { kind: "bold", re: /\*\*([^*]+)\*\*/ },
  { kind: "italic", re: /\*([^*]+)\*/ },
  { kind: "auto", re: /(https?:\/\/[^\s)]+)/ },
] as const;

function renderInline(text: string, onNavigate: (() => void) | undefined, keyBase: string): ReactNode[] {
  if (!text) return [];

  let best: { kind: string; index: number; m: RegExpMatchArray } | null = null;
  for (const { kind, re } of INLINE) {
    const m = text.match(re);
    if (m && m.index != null && (best == null || m.index < best.index)) {
      best = { kind, index: m.index, m };
    }
  }
  if (!best) return [text];

  const before = text.slice(0, best.index);
  const after = text.slice(best.index + best.m[0].length);
  const k = `${keyBase}-${best.index}`;
  let node: ReactNode;

  if (best.kind === "code") {
    node = <code key={k} className="latin" dir="ltr">{best.m[1]}</code>;
  } else if (best.kind === "bold") {
    node = <strong key={k}>{renderInline(best.m[1], onNavigate, `${k}b`)}</strong>;
  } else if (best.kind === "italic") {
    node = <em key={k}>{renderInline(best.m[1], onNavigate, `${k}i`)}</em>;
  } else if (best.kind === "link") {
    node = renderLink(best.m[1], best.m[2], onNavigate, k);
  } else {
    node = renderLink(best.m[1], best.m[1], onNavigate, k);
  }

  return [before, node, ...renderInline(after, onNavigate, `${keyBase}+`)];
}

function renderLink(label: string, href: string, onNavigate: (() => void) | undefined, key: string): ReactNode {
  const inner = <Bdi>{label}</Bdi>;
  if (href.startsWith("/")) {
    // Internal route — navigate in-app and let the caller close a floating panel.
    return (
      <Link key={key} to={href} className="assistant-md__link" onClick={onNavigate}>
        {inner}
      </Link>
    );
  }
  return (
    <a key={key} href={href} className="assistant-md__link" target="_blank" rel="noopener noreferrer">
      {inner}
    </a>
  );
}

// --- block structure ---------------------------------------------------------------------------

function renderBlocks(
  src: string,
  onNavigate: (() => void) | undefined,
  copyCode: (code: string) => void,
  copyLabel: string,
): ReactNode[] {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;

  const isTableSep = (s: string) => /^\s*\|?[\s:]*-{1,}[\s:|-]*\|?\s*$/.test(s) && s.includes("-");

  while (i < lines.length) {
    const line = lines[i];

    // Blank — skip; paragraph breaks come from grouping below.
    if (!line.trim()) {
      i++;
      continue;
    }

    // Fenced code block.
    const fence = line.match(/^\s*```/);
    if (fence) {
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++]);
      if (i < lines.length) i++; // closing fence
      const code = body.join("\n");
      out.push(
        <div key={key++} className="assistant-code-block">
          <button
            type="button"
            className="assistant-code-block__copy"
            aria-label={copyLabel}
            onClick={() => copyCode(code)}
          >
            <NavIcon name="duplicate" />
          </button>
          <pre className="assistant-code latin" dir="ltr">
            <code>{code}</code>
          </pre>
        </div>,
      );
      continue;
    }

    // Heading (### …) — rendered as an <h4> so it never competes with page headings.
    const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
    if (heading) {
      out.push(
        <h4 key={key++} className="assistant-md__h" dir="auto">
          {renderInline(heading[1].trim(), onNavigate, `h${key}`)}
        </h4>,
      );
      i++;
      continue;
    }

    // GFM table: a header row, a separator row, then body rows.
    if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const cells = (row: string) =>
        row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const header = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push(
        <div key={key++} className="assistant-md__table-wrap">
          <table className="assistant-md__table">
            <thead>
              <tr>
                {header.map((c, ci) => (
                  <th key={ci} dir="auto">{renderInline(c, onNavigate, `th${key}-${ci}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>
                  {r.map((c, ci) => (
                    <td key={ci} dir="auto">{renderInline(c, onNavigate, `td${key}-${ri}-${ci}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Lists (unordered `- ` / ordered `1. `), one nesting level by indentation.
    const listMatch = line.match(/^(\s*)([-*]|\d+\.)\s+/);
    if (listMatch) {
      const ordered = /\d/.test(listMatch[2]);
      const items: ReactNode[] = [];
      while (i < lines.length) {
        const m = lines[i].match(/^(\s*)(?:[-*]|\d+\.)\s+(.*)$/);
        if (!m) break;
        const nested = m[1].length >= 2;
        items.push(
          <li key={items.length} className={nested ? "assistant-md__li--nested" : undefined} dir="auto">
            {renderInline(m[2], onNavigate, `li${key}-${items.length}`)}
          </li>,
        );
        i++;
      }
      out.push(
        ordered ? (
          <ol key={key++} className="assistant-md__list">{items}</ol>
        ) : (
          <ul key={key++} className="assistant-md__list">{items}</ul>
        ),
      );
      continue;
    }

    // Paragraph — gather consecutive plain lines, keep soft line breaks inside.
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^\s*```/.test(lines[i]) &&
      !/^\s*#{1,6}\s+/.test(lines[i]) &&
      !/^(\s*)([-*]|\d+\.)\s+/.test(lines[i]) &&
      !(/^\s*\|.*\|\s*$/.test(lines[i]) && i + 1 < lines.length && isTableSep(lines[i + 1]))
    ) {
      para.push(lines[i++]);
    }
    out.push(
      <p key={key++} className="assistant-md__p" dir="auto">
        {para.map((ln, li) => (
          <Fragment key={li}>
            {li > 0 && <br />}
            {renderInline(ln, onNavigate, `p${key}-${li}`)}
          </Fragment>
        ))}
      </p>,
    );
  }

  return out;
}
