import { apiFetch } from "./client";

export interface Me {
  id: number;
  username: string;
  email: string;
  roles: string[];
  is_2fa_enabled: boolean;
  branch: string | null;
}

export function getMe(): Promise<Me> {
  return apiFetch<Me>("/identity/me");
}
