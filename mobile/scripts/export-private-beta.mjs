import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

// Browser sign-in uses the API cookie on the same origin. Never inherit the
// different API address used by Expo Go, or an anonymous prototype build flag.
/** @param {Record<string, string | undefined>} env
 * @returns {Record<string, string | undefined>} */
export function privateBetaWebEnv(env = process.env) {
  return { ...env, EXPO_PUBLIC_PRIVATE_BETA: '1', EXPO_PUBLIC_API_URL: '/' };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = spawnSync(process.execPath, [
    fileURLToPath(new URL('../node_modules/expo/bin/cli', import.meta.url)),
    'export', '--platform', 'web', '--clear', '--output-dir', '.beta-dist',
  ], {
    cwd: fileURLToPath(new URL('../', import.meta.url)),
    env: privateBetaWebEnv(),
    stdio: 'inherit',
  });
  if (result.error) console.error(result.error.message);
  process.exitCode = result.status ?? 1;
}
