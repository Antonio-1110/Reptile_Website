import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ResetPasswordPage from './ResetPasswordPage';
import VerifyEmailPage from './VerifyEmailPage';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const at = (url) => ({ wrapper: ({ children }) => <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter> });

describe('VerifyEmailPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('sends the link back to the API and shows the result', async () => {
    const fetchMock = vi.fn(async () => json({ detail: 'Your email address is confirmed.' }));
    vi.stubGlobal('fetch', fetchMock);
    render(<VerifyEmailPage />, at('/verify-email?uid=MQ&token=abc'));

    expect(await screen.findByText('Your email address is confirmed.')).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ uid: 'MQ', token: 'abc' });
  });

  it('explains an expired link', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ detail: 'This link is invalid or has expired.' }, 400)));
    render(<VerifyEmailPage />, at('/verify-email?uid=MQ&token=old'));
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or has expired');
  });

  it('says so when the link is cut off', () => {
    vi.stubGlobal('fetch', vi.fn());
    render(<VerifyEmailPage />, at('/verify-email?uid=MQ'));
    expect(screen.getByRole('alert')).toHaveTextContent('incomplete');
  });
});

describe('ResetPasswordPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  const fill = (password, confirm = password) => {
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: password } });
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: confirm } });
    fireEvent.click(screen.getByRole('button', { name: 'Save password' }));
  };

  it('checks both passwords match before sending', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<ResetPasswordPage />, at('/reset-password?uid=MQ&token=abc'));
    fill('BrandNew!567', 'Different!890');
    expect(screen.getByText("Passwords don't match.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows the password rules the backend applies', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ password: ['This password is too common.'] }, 400)));
    render(<ResetPasswordPage />, at('/reset-password?uid=MQ&token=abc'));
    fill('password');
    expect(await screen.findByText('This password is too common.')).toBeInTheDocument();
  });

  it('confirms the change', async () => {
    const fetchMock = vi.fn(async () => json({ detail: 'Your password has been changed.' }));
    vi.stubGlobal('fetch', fetchMock);
    render(<ResetPasswordPage />, at('/reset-password?uid=MQ&token=abc'));
    fill('BrandNew!567');
    expect(await screen.findByRole('status')).toHaveTextContent('Your password has been changed.');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ uid: 'MQ', token: 'abc', password: 'BrandNew!567' });
  });
});
