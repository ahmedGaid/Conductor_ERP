import { useTranslation } from "react-i18next";
import { Checkbox } from "./Checkbox";

/**
 * The leading selection column shared by every list table (sales>orders is the reference).
 * Pair with `useRowSelection`: `SelectAllCell` in `<thead>` drives select-all/tri-state,
 * `SelectRowCell` in each `<tr>` drives toggle/Shift-range. `className` is the table's own
 * `*-table__select` class — print.css hides the column by that selector, data-surfaces.css
 * sizes it, so every new table prefix must be added to both.
 */
export function SelectAllCell({
  className,
  allSelected,
  someSelected,
  onToggleAll,
}: {
  className: string;
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: () => void;
}) {
  const { t } = useTranslation();
  return (
    <th className={className}>
      <Checkbox checked={allSelected} indeterminate={someSelected} onChange={onToggleAll} label={t("bulk.selectAll")} />
    </th>
  );
}

export function SelectRowCell({
  className,
  checked,
  onToggle,
}: {
  className: string;
  checked: boolean;
  onToggle: (shiftKey: boolean) => void;
}) {
  const { t } = useTranslation();
  return (
    <td className={className}>
      <Checkbox checked={checked} onChange={(_next, shiftKey) => onToggle(shiftKey)} label={t("bulk.selectRow")} />
    </td>
  );
}
