export { IS_WINDOWS, winCmd } from './platform.js';
export {
  writeFileSafe,
  copyIfExists,
  findMissingPaths,
  findEmptyPaths,
  sha256,
  sha256WithSalt,
  generateSalt,
} from './fs-helpers.js';
