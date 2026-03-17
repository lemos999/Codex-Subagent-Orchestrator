/**
 * Manifest writer — produces orchestration-manifest.json matching PS launcher format.
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import type { Manifest } from '../types/manifest.js';

/**
 * Write the orchestration manifest as JSON.
 * Ensures output directory exists and uses UTF-8 encoding.
 */
export async function writeManifest(
  filePath: string,
  manifest: Manifest,
): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const json = JSON.stringify(manifest, null, 4);
  await fs.writeFile(filePath, json, 'utf8');
}
