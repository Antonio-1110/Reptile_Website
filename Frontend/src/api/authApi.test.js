import { afterEach, describe, expect, it, vi } from 'vitest';
import { authFetch, isLoggedIn, login, logout } from './authApi';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

describe('authFetch', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('turns DRF field errors into error.fields and a readable message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ username: ['A user with that username already exists.'] }, 400)));
    const error = await authFetch('/x/').catch((caught) => caught);
    expect(error.status).toBe(400);
    expect(error.fields).toEqual({ username: 'A user with that username already exists.' });
    expect(error.message).toBe('A user with that username already exists.');
  });

  it('uses "detail" as the message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ detail: 'Nope.' }, 403)));
    const error = await authFetch('/x/').catch((caught) => caught);
    expect(error.message).toBe('Nope.');
  });

  it('refreshes an expired access token once and retries', async () => {
    localStorage.setItem('accessToken', 'old');
    localStorage.setItem('refreshToken', 'refresh-me');
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(json({ access: 'new' }))
      .mockResolvedValueOnce(json({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(authFetch('/x/')).resolves.toEqual({ ok: true });
    expect(localStorage.getItem('accessToken')).toBe('new');
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer new');
  });

  it('does not set a JSON content type on FormData uploads', async () => {
    const fetchMock = vi.fn(async () => json({}));
    vi.stubGlobal('fetch', fetchMock);
    await authFetch('/x/', { method: 'POST', body: new FormData() });
    expect(fetchMock.mock.calls[0][1].headers['Content-Type']).toBeUndefined();
  });
});

describe('login / logout', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('stores both tokens on login and clears them on logout', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ access: 'a', refresh: 'r' })));
    await login('user', 'pass');
    expect(isLoggedIn()).toBe(true);
    logout();
    expect(isLoggedIn()).toBe(false);
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });
});
