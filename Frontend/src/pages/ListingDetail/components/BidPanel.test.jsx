import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BidPanel from './BidPanel';
import { payDeposit, placeBid } from '../../../api/auctionsApi';

vi.mock('../../../api/auctionsApi', () => ({
  cancelAuction: vi.fn(),
  payDeposit: vi.fn(),
  placeBid: vi.fn(),
}));

const auction = (fields = {}) => ({
  id: 7, currency: 'TWD', minimumNextBid: '5000.00', minIncrement: '100.00', depositAmount: '500.00',
  bidCount: 2, isSeller: false, myDeposit: { status: 'held' }, extendWindowMinutes: 0, ...fields,
});

function renderPanel(props = {}) {
  const handlers = { onChanged: vi.fn(), showToast: vi.fn() };
  render(
    <BidPanel auction={auction()} phase="live" topBid={null} hasOwnBid={false} {...handlers} {...props} />,
    { wrapper: MemoryRouter },
  );
  return handlers;
}

describe('BidPanel', () => {
  beforeEach(() => {
    localStorage.setItem('accessToken', 'token');
  });

  it('asks visitors to sign in before bidding', () => {
    localStorage.removeItem('accessToken');
    renderPanel();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', expect.stringContaining('/signin?next='));
    expect(screen.queryByRole('button', { name: 'Place bid' })).not.toBeInTheDocument();
  });

  it('asks for the deposit before a bid can be placed, and pays it', async () => {
    payDeposit.mockResolvedValue({ deposit: { status: 'held' }, payment: {} });
    const { onChanged, showToast } = renderPanel({ auction: auction({ myDeposit: null }) });
    expect(screen.queryByRole('button', { name: 'Place bid' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Pay NT$500 deposit' }));
    await waitFor(() => expect(showToast).toHaveBeenCalledWith('Deposit paid — you can bid now.'));
    expect(payDeposit).toHaveBeenCalledWith(7);
    expect(onChanged).toHaveBeenCalled();
  });

  it('refuses an amount below the minimum without calling the server', () => {
    renderPanel();
    fireEvent.change(screen.getByLabelText(/Your bid/), { target: { value: '4900' } });
    expect(screen.getByText(/at least NT\$5,000/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Place bid' })).toBeDisabled();
    expect(placeBid).not.toHaveBeenCalled();
  });

  it('places a bid only after it is confirmed', async () => {
    placeBid.mockResolvedValue({});
    const { showToast } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'NT$5,300' })); // quick pick: minimum + 3 increments
    fireEvent.click(screen.getByRole('button', { name: 'Place bid' }));
    expect(placeBid).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirm bid' }));
    await waitFor(() => expect(placeBid).toHaveBeenCalledWith(7, '5300'));
    expect(showToast).toHaveBeenCalled();
  });

  it('shows why the server refused a bid and reloads the auction', async () => {
    placeBid.mockRejectedValue(new Error('Your bid must be at least NT$5,100.'));
    const { onChanged } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'Place bid' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm bid' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Your bid must be at least NT$5,100.');
    expect(onChanged).toHaveBeenCalled();
  });

  it('tells the top bidder they lead', () => {
    renderPanel({ topBid: { isMine: true }, hasOwnBid: true });
    expect(screen.getByText("You're the highest bidder.")).toBeInTheDocument();
  });

  it('tells a bidder when someone else has outbid them', () => {
    renderPanel({ topBid: { isMine: false }, hasOwnBid: true });
    expect(screen.getByText("You've been outbid.")).toBeInTheDocument();
  });

  it('lets a seller cancel only while nobody has bid', () => {
    renderPanel({ auction: auction({ isSeller: true, bidCount: 0 }) });
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('does not let a seller cancel once someone has bid', () => {
    renderPanel({ auction: auction({ isSeller: true, bidCount: 3 }) });
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
  });
});
