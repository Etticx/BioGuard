import type { Session, User } from './reportContract';
import { RequestError, SessionExpired } from './requestErrors';

export class AccountReadError extends Error {}

export function parseUser(value: unknown): User {
  if (!value || typeof value !== 'object') throw new AccountReadError('Could not read your account.');
  const raw = value as Omit<Partial<User>, 'role'> & { role?: string };
  const user = { ...raw, role: raw.role === 'officer' ? 'management' : raw.role };
  if (typeof user.id !== 'string' || !user.id || typeof user.username !== 'string' ||
      typeof user.display_name !== 'string' || !['ground', 'ecology', 'management'].includes(user.role ?? '')) {
    throw new AccountReadError('Could not read your account.');
  }
  return user as User;
}
export function parseSession(value: unknown): Session {
  const session = value as Partial<Session> | null;
  if (!session || typeof session.token !== 'string' || !session.token) throw new Error('Could not sign in.');
  return { token: session.token, user: parseUser(session.user) };
}
export function workspaceFor(user: User): 'password' | 'ground' | 'ecology' | 'management' {
  return user.must_change_password ? 'password' : user.role;
}
export function sessionHeaders(session?: Session): Record<string, string> {
  return session?.token ? { Authorization: 'Bearer ' + session.token } : {};
}
export function officerUrl(apiBase: string, browserOrigin?: string): string {
  const api = new URL(apiBase || '/', browserOrigin);
  if (!['http:', 'https:'].includes(api.protocol) || api.username || api.password) throw new Error('Check the server address.');
  return new URL('/officer', api).href;
}
export function isOfficerPage(url: string, expected: string): boolean {
  try { const actual = new URL(url); const target = new URL(expected); return actual.origin === target.origin && actual.pathname === '/officer'; }
  catch { return false; }
}

export function canonicalWebEntry(apiBase: string, browserOrigin: string, privateBeta: boolean): string | null {
  if (!privateBeta) return null;
  const destination = new URL(officerUrl(apiBase, browserOrigin));
  return destination.origin === browserOrigin ? null : new URL('/', destination).href;
}

export function shouldForgetSession(error: unknown): boolean {
  return error instanceof SessionExpired || error instanceof AccountReadError ||
    (error instanceof RequestError && [401, 403].includes(error.status));
}
