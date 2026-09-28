import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ChooseUsernamePage from './ChooseUsernamePage';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/choose-username" element={<ChooseUsernamePage />} />
        <Route path="*" element={<p>Arrived</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ChooseUsernamePage', () => {
  beforeEach(() => localStorage.setItem('accessToken', 'a'));
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('suggests the current username and keeps it without saving', async () => {
    const fetchMock = vi.fn(async () => json({ username: 'jane.chen' }));
    vi.stubGlobal('fetch', fetchMock);
    renderAt('/choose-username?next=%2Forders');

    expect(await screen.findByLabelText('Username')).toHaveValue('jane.chen');
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText('Arrived')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('saves a new username and continues', async () => {
    const fetchMock = vi.fn(async (url, options) => json(
      options?.method === 'PATCH' ? { username: 'gecko_fan' } : { username: 'jane.chen' },
    ));
    vi.stubGlobal('fetch', fetchMock);
    renderAt('/choose-username');

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: ' gecko_fan ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText('Arrived')).toBeInTheDocument();
    const [, patch] = fetchMock.mock.calls[1];
    expect(patch.method).toBe('PATCH');
    expect(JSON.parse(patch.body)).toEqual({ username: 'gecko_fan' });
  });

  it('shows why a username was refused', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url, options) => (
      options?.method === 'PATCH'
        ? json({ username: ['A user with that username already exists.'] }, 400)
        : json({ username: 'jane.chen' })
    )));
    renderAt('/choose-username');

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'taken' } });
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText('A user with that username already exists.')).toBeInTheDocument();
    expect(screen.queryByText('Arrived')).not.toBeInTheDocument();
  });
});
