import { SessionExpired } from './requestErrors';
import { sessionHeaders } from './roleAccess';
import type { Session } from './reportContract';
import Constants from 'expo-constants';
import { File } from 'expo-file-system';
import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';
import { parseIdentification, resolveApiUrl } from './contract';

const apiUrl = resolveApiUrl(
  process.env.EXPO_PUBLIC_API_URL,
  Constants.expoConfig?.hostUri,
);

export async function identifyPhoto(uri: string, signal: AbortSignal, session?: Session) {
  const photo = Platform.OS === 'web'
    ? await (await fetch(uri, { signal })).blob()
    : new File(uri);
  if (photo.size > 12 * 1024 * 1024) {
    throw new Error('This photo is too large. Try a smaller photo.');
  }
  const response = await fetch(apiUrl + '/identify', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'image/jpeg', Accept: 'application/json', ...sessionHeaders(session) },
    body: photo,
    signal,
  });
  if(response.status===401&&session)throw new SessionExpired('Your session ended. Sign in again.');
  if (!response.ok) {
    let message = 'Could not identify this photo. Please try again.';
    try {
      const error = await response.json() as { detail?: unknown };
      if (typeof error.detail === 'string') message = error.detail;
    } catch { /* The server may return a non-JSON error. */ }
    throw new Error(message);
  }
  try {
    return parseIdentification(await response.json());
  } catch {
    throw new Error('Could not read the result. Please try again.');
  }
}
