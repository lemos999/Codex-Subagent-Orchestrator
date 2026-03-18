/**
 * Manifest writer — produces orchestration-manifest.json matching PS launcher format.
 */

import type { Manifest } from '../types/manifest.js';
import { writeFileSafe } from '../common/fs-helpers.js';

/**
 * Write the orchestration manifest as JSON.
 * Ensures output directory exists and uses UTF-8 encoding.
 */
export async function writeManifest(
  filePath: string,
  manifest: Manifest,
): Promise<void> {
  await writeFileSafe(filePath, JSON.stringify(manifest, null, 4));
}
