import { describe, expect, it } from 'vitest';
import { rootErrorOptions, scrubBreadcrumb, scrubEvent, scrubUrl } from './sentry.js';

describe('sentry scrubbing', () => {
  it('drops the query string and hash from URLs', () => {
    expect(scrubUrl('https://www.reptilian.app/reset-password?uid=MQ&token=abc#x'))
      .toBe('https://www.reptilian.app/reset-password');
    expect(scrubUrl('/marketplace#top')).toBe('/marketplace');
    expect(scrubUrl(undefined)).toBeUndefined();
  });

  it('removes tokens from the page URL, query string, cookies and referrer of an event', () => {
    const event = scrubEvent({
      request: {
        url: 'https://www.reptilian.app/verify-email?uid=MQ&token=abc',
        query_string: 'uid=MQ&token=abc',
        cookies: { a: 'b' },
        headers: { Referer: 'https://www.reptilian.app/reset-password?token=abc', 'User-Agent': 'x' },
      },
    });
    expect(event.request).toEqual({
      url: 'https://www.reptilian.app/verify-email',
      headers: { Referer: 'https://www.reptilian.app/reset-password', 'User-Agent': 'x' },
    });
  });

  it('removes tokens from navigation and request breadcrumbs', () => {
    expect(scrubBreadcrumb({ category: 'navigation', data: { from: '/signin?next=%2Forders', to: '/reset-password?token=abc' } }).data)
      .toEqual({ from: '/signin', to: '/reset-password' });
    expect(scrubBreadcrumb({ category: 'fetch', data: { url: 'https://api.reptilian.app/api/v1/posts/?search=gecko', method: 'GET' } }).data)
      .toEqual({ url: 'https://api.reptilian.app/api/v1/posts/', method: 'GET' });
  });

  it('leaves React error handling alone when no DSN is configured', () => {
    expect(rootErrorOptions()).toEqual({});
  });
});
