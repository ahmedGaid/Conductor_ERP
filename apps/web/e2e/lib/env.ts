// Reads process.env without requiring @types/node as a project devDependency (this repo's Node
// typings gap — see DECISIONS.md; the founder approved only @playwright/test as a new dependency).
// Works identically at runtime; Node's real `process` global is present when Playwright runs.
export function env(name: string): string | undefined {
  return (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.[name];
}
