import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ChangePasswordPage from './ChangePasswordPage';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const inRouter = { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> };

// The profile request, then whatever `answer` gives for the change or link request.
function stubApi(profile, answer) {
  const fetchMock = vi.fn(async (url) => (String(url).includes('/account/profile/')
    ? json({ email: 'mei@example.com', has_password: true, ...profile })
    : answer()));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const lastBody = (fetchMock) => JSON.parse(fetchMock.mock.calls.at(-1)[1].body);

describe('ChangePasswordPage', () => {
  beforeEach(() => localStorage.setItem('accessToken', 'old-access'));
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  const fill = async ({ current = 'OldPass!234', password = 'BrandNew!567', confirm = password } = {}) => {
    fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: current } });
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: password } });
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: confirm } });
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }));
  };

  it('sends the current and new password, and keeps this device signed in', async () => {
    const fetchMock = stubApi({}, () => json({ detail: 'Changed.', access: 'new-access', refresh: 'new-refresh' }));
    render(<ChangePasswordPage />, inRouter);
    await fill();

    expect(await screen.findByRole('status')).toHaveTextContent('other devices have been signed out');
    expect(lastBody(fetchMock)).toEqual({ current_password: 'OldPass!234', password: 'BrandNew!567' });
    expect(localStorage.getItem('accessToken')).toBe('new-access');
    expect(localStorage.getItem('refreshToken')).toBe('new-refresh');
  });

  it('checks both new passwords match before sending', async () => {
    const fetchMock = stubApi({}, () => json({}));
    render(<ChangePasswordPage />, inRouter);
    await fill({ confirm: 'Different!890' });

    expect(screen.getByText("Passwords don't match.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('shows a wrong current password under that field', async () => {
    stubApi({}, () => json({ current_password: ['Your current password is incorrect.'] }, 400));
    render(<ChangePasswordPage />, inRouter);
    await fill({ current: 'Guess!1234' });

    expect(await screen.findByText('Your current password is incorrect.')).toBeInTheDocument();
    expect(screen.getByLabelText(/^Current password/)).toHaveAttribute('aria-invalid', 'true');
  });

  it('emails a link to accounts without a password', async () => {
    const fetchMock = stubApi({ has_password: false }, () => json({ detail: 'Sent.' }));
    render(<ChangePasswordPage />, inRouter);

    expect(await screen.findByRole('heading', { name: 'Set a password' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Current password')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Email me a link' }));

    expect(await screen.findByRole('status')).toHaveTextContent('mei@example.com');
    expect(String(fetchMock.mock.calls.at(-1)[0])).toContain('/auth/password-reset/');
    expect(lastBody(fetchMock)).toEqual({ email: 'mei@example.com' });
  });

  it('emails a link when the current password is forgotten', async () => {
    const fetchMock = stubApi({}, () => json({ detail: 'Sent.' }));
    render(<ChangePasswordPage />, inRouter);
    fireEvent.click(await screen.findByRole('button', { name: 'Forgot your current password?' }));

    expect(await screen.findByRole('status')).toHaveTextContent('mei@example.com');
    expect(lastBody(fetchMock)).toEqual({ email: 'mei@example.com' });
  });
});
