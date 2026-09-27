import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// The client ID is read when the module loads, so each test imports a fresh copy after stubbing it.
async function renderButton(clientId, props = {}) {
  vi.resetModules();
  vi.stubEnv('VITE_GOOGLE_CLIENT_ID', clientId);
  const { default: GoogleSignInButton } = await import('./GoogleSignInButton');
  return render(<GoogleSignInButton onCredential={() => {}} {...props} />);
}

describe('GoogleSignInButton', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    delete window.google;
  });

  it('shows nothing until a client ID is configured', async () => {
    const { container } = await renderButton('');
    expect(container).toBeEmptyDOMElement();
  });

  it("draws Google's button and passes the credential on", async () => {
    const google = { accounts: { id: { initialize: vi.fn(), renderButton: vi.fn() } } };
    window.google = google;
    const onCredential = vi.fn();

    await renderButton('client-123', { onCredential });

    await waitFor(() => expect(google.accounts.id.renderButton).toHaveBeenCalled());
    expect(screen.getByText('or')).toBeInTheDocument();
    const { client_id: clientId, callback } = google.accounts.id.initialize.mock.calls[0][0];
    expect(clientId).toBe('client-123');
    callback({ credential: 'google-id-token' });
    expect(onCredential).toHaveBeenCalledWith('google-id-token');
  });

  it("says so when Google's script can't load", async () => {
    const append = document.head.appendChild.bind(document.head);
    vi.spyOn(document.head, 'appendChild').mockImplementation((node) => {
      const result = append(node);
      if (node.tagName === 'SCRIPT') setTimeout(() => node.onerror?.());
      return result;
    });

    await renderButton('client-123');

    expect(await screen.findByRole('alert')).toHaveTextContent("Google sign-in couldn't load");
    vi.restoreAllMocks();
  });
});
