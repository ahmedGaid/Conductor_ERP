import type { TFunction } from "i18next";

const BUILTIN_ROLES: Record<string, string> = {
  "System Admin": "admin.roles.names.systemAdmin",
  "Branch Manager": "admin.roles.names.branchManager",
  Accountant: "admin.roles.names.accountant",
  Auditor: "admin.roles.names.auditor",
};

export function roleLabel(name: string, t: TFunction): string {
  return t(BUILTIN_ROLES[name] ?? name);
}
