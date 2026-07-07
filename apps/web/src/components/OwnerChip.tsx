import { Bdi } from "./Bdi";
import { Tooltip } from "./Tooltip";
import "./metaCells.css";

/**
 * Owner initials — first grapheme of the first two words, Arabic-aware (`[...word]` splits by code
 * point, not UTF-16 unit, so an Arabic first letter survives). Latin initials are upper-cased;
 * Arabic has no case, so `toUpperCase()` is a no-op there.
 */
export function ownerInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "؟"; // designed fallback, never a blank chip
  const first = [...words[0]][0] ?? "";
  const second = words.length > 1 ? ([...words[1]][0] ?? "") : "";
  return (first + second).toUpperCase();
}

/**
 * Monochrome owner chip — a quiet initials circle (no photos; avatars need an upload backend, a
 * follow-up plan). Full name on hover; the chip carries an `aria-label` so the name reaches AT
 * without a tab stop in dense tables. `<Bdi>` keeps Latin initials upright inside RTL rows.
 */
export function OwnerChip({ name }: { name: string }) {
  const initials = ownerInitials(name);
  return (
    <Tooltip label={name}>
      <span className="meta-owner" aria-label={name}>
        <Bdi>{initials}</Bdi>
      </span>
    </Tooltip>
  );
}
