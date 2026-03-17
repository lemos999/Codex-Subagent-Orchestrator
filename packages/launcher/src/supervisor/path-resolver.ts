/**
 * Path resolver — resolves spec paths to absolute paths.
 * Handles cwd_resolution modes: 'invocation' and 'spec'.
 */

import * as path from 'node:path';
import type { LauncherSpec } from '../types/spec.js';
import type { ResolvedPaths } from '../types/state.js';

/**
 * Resolve all paths from a launcher spec to absolute paths.
 *
 * @param spec - The parsed launcher spec
 * @param invocationCwd - The directory from which the CLI was invoked
 * @param specFilePath - The absolute path to the spec JSON file
 */
export function resolvePaths(
  spec: LauncherSpec,
  invocationCwd: string,
  specFilePath: string,
): ResolvedPaths {
  const cwdResolution = spec.cwd_resolution ?? 'invocation';
  const specDirectory = path.dirname(path.resolve(specFilePath));

  // Determine the resolution base
  const resolutionBase =
    cwdResolution === 'spec' ? specDirectory : path.resolve(invocationCwd);

  // Resolve workspace root (the cwd field in spec)
  const workspaceRoot = path.resolve(resolutionBase, spec.cwd);

  // Resolve output_dir (relative to workspace root)
  const outputDir = spec.output_dir
    ? path.resolve(workspaceRoot, spec.output_dir)
    : path.resolve(workspaceRoot, 'subagent-runs');

  // Resolve manifest file
  const manifestFile = spec.manifest_file
    ? path.resolve(outputDir, spec.manifest_file)
    : path.resolve(outputDir, 'orchestration-manifest.json');

  // Resolve summary file
  const summaryFile =
    spec.write_summary_file !== false
      ? spec.summary_file
        ? path.resolve(outputDir, spec.summary_file)
        : path.resolve(outputDir, 'orchestration-summary.md')
      : null;

  // Resolve debug log file
  const debugLogFile = spec.debug_log_file
    ? path.resolve(outputDir, spec.debug_log_file)
    : null;

  // Resolve archive root
  const archiveRoot = spec.archive_root
    ? path.resolve(workspaceRoot, spec.archive_root)
    : null;

  return {
    workspaceRoot,
    outputDir,
    manifestFile,
    summaryFile,
    debugLogFile,
    archiveRoot,
    specPath: path.resolve(specFilePath),
    specDirectory,
    invocationCwd: path.resolve(invocationCwd),
  };
}
