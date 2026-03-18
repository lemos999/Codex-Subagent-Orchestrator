/**
 * Platform detection and CLI tool resolution utilities.
 * Centralizes Windows-specific logic that was previously duplicated
 * across spawn.ts and hooks.ts.
 */

/** True when running on Windows. */
export const IS_WINDOWS = process.platform === 'win32';

/**
 * npm-installed CLI tools that require a .cmd extension on Windows.
 * Native binaries (like claude.exe) do NOT need this suffix.
 */
const NPM_CLI_TOOLS = new Set(['codex', 'npx']);

/**
 * Resolve a CLI command name for the current platform.
 * On Windows, npm-installed tools need the `.cmd` suffix for child_process.spawn.
 */
export function winCmd(name: string): string {
  if (IS_WINDOWS && NPM_CLI_TOOLS.has(name)) {
    return `${name}.cmd`;
  }
  return name;
}
