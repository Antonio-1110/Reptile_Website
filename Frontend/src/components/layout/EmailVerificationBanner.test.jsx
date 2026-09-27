import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EmailVerificationBanner from './EmailVerificationBanner';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

describe('EmailVerificationBanner', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('asks an unverified user to confirm and sends a new link', async () => {
    localStorage.setItem('accessToken', 'a');
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json({ email_verified: false }))
      .mockResolvedValueOnce(json({ detail: "We've sent a new link to me@example.com." }));
    vi.stubGlobal('fetch', fetchMock);
    render(<EmailVerificationBanner />);

    fireEvent.click(await screen.findByRole('button', { name: 'Send a new link' }));

    expect(await screen.findByRole('status')).toHaveTextContent('me@example.com');
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/auth\/verify-email\/resend\/$/);
  });

  it('stays hidden once the address is confirmed', async () => {
    localStorage.setItem('accessToken', 'a');
    const fetchMock = vi.fn(async () => json({ email_verified: true }));
    vi.stubGlobal('fetch', fetchMock);
    const { container } = render(<EmailVerificationBanner />);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('does not ask signed-out visitors anything', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const { container } = render(<EmailVerificationBanner />);
    expect(container).toBeEmptyDOMElement();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
