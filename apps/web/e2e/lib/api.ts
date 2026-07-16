import type { APIRequestContext } from "@playwright/test";

import { env } from "./env";

const USERNAME = env("E2E_ADMIN_USERNAME") ?? "admin";
const PASSWORD = env("E2E_ADMIN_PASSWORD") ?? "Dev12345!";

// The access token lives only in memory in the app (never persisted — see api/client.ts), so a
// spec can't read it out of storageState.
//
// This logs in fresh rather than replaying the saved refresh cookie through `/token/refresh`:
// SimpleJWT rotates AND blacklists refresh tokens on use (ROTATE_REFRESH_TOKENS +
// BLACKLIST_AFTER_ROTATION — see config/settings/base.py), and the SAME browser page
// independently refreshes on its own boot (its in-memory access token resets per page/tab even
// though the context's cookies persist worker-wide). Two refreshes racing on the same cookie at
// once made this flaky ("Token is blacklisted") in practice; a plain login has no such shared,
// single-use state to race against.
export async function freshAccessToken(request: APIRequestContext): Promise<string> {
  const res = await request.post("/api/identity/login", {
    data: { username: USERNAME, password: PASSWORD, otp_code: "" },
  });
  if (!res.ok()) throw new Error(`login failed: ${res.status()} ${await res.text()}`);
  const body = (await res.json()) as { data?: { access?: string } };
  if (!body.data?.access) throw new Error("login returned no access token");
  return body.data.access;
}

export type ApiGet = <T>(path: string) => Promise<T>;
export type ApiPost = <T>(path: string, body: unknown) => Promise<T>;

/** GET `/api<path>`, unwrapping the `{data}` envelope every endpoint returns (see api/client.ts). */
export async function apiGet<T>(request: APIRequestContext, path: string, token: string): Promise<T> {
  const res = await request.get(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok()) throw new Error(`GET ${path} failed: ${res.status()} ${await res.text()}`);
  const body = (await res.json()) as { data: T };
  return body.data;
}

/** POST `/api<path>`, unwrapping the `{data}` envelope every endpoint returns (see api/client.ts). */
export async function apiPost<T>(
  request: APIRequestContext,
  path: string,
  body: unknown,
  token: string,
): Promise<T> {
  const res = await request.post(`/api${path}`, {
    data: body,
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok()) throw new Error(`POST ${path} failed: ${res.status()} ${await res.text()}`);
  const json = (await res.json()) as { data: T };
  return json.data;
}
