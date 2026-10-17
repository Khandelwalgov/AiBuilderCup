import { fileURLToPath } from 'node:url';
export const artifactRoot = fileURLToPath(
  new URL('../../../.live-validation/', import.meta.url),
).replace(/\/$/, '');
