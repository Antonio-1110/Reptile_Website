import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import OrderPanel from './OrderPanel';
import { confirmReceived, markHandedOver, payOrder, reportProblem } from '../../../api/auctionsApi';

vi.mock('../../../api/auctionsApi', () => ({
  confirmReceived: vi.fn(async () => ({})),
  decideRunnerUp: vi.fn(async () => ({})),
  declineOffer: vi.fn(async () => ({})),
  markHandedOver: vi.fn(async () => ({})),
  payOrder: vi.fn(async () => ({})),
  reportProblem: vi.fn(async () => ({})),
}));

const order = (fields = {}) => ({
  id: 3, role: 'buyer', status: 'awaiting_payment', balanceStatus: 'unpaid', currency: 'TWD',
  price: '8000.00', balance: '7500.00', depositAmount: '500.00',
  paymentDueAt: new Date('2026-10-01T12:00:00Z'), counterpart: null, ...fields,
});

function renderPanel(fields, category) {
  const handlers = { onChanged: vi.fn(), onToast: vi.fn() };
  render(<OrderPanel order={order(fields)} category={category} {...handlers} />);
  return handlers;
}

describe('OrderPanel', () => {
  it('lets the winner pay the balance that is left after the deposit', async () => {
    const { onToast } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'Pay NT$7,500' }));
    await waitFor(() => expect(payOrder).toHaveBeenCalledWith(3));
    expect(onToast).toHaveBeenCalledWith('Payment received.');
  });

  it("doesn't offer to pay again while a payment is on its way", () => {
    renderPanel({ balanceStatus: 'pending' });
    expect(screen.queryByRole('button', { name: /^Pay / })).not.toBeInTheDocument();
    expect(screen.getByText(/Waiting for your NT\$7,500 payment/)).toBeInTheDocument();
  });

  it('lets the seller mark a paid order as handed over, with a tracking note', async () => {
    renderPanel({ role: 'seller', status: 'paid', handoverDueAt: new Date('2026-10-05T12:00:00Z') });
    fireEvent.change(screen.getByLabelText(/Courier and tracking number/), { target: { value: 'Black Cat 1234' } });
    fireEvent.click(screen.getByRole('button', { name: "I've handed it over / shipped it" }));
    await waitFor(() => expect(markHandedOver).toHaveBeenCalledWith(3, 'Black Cat 1234'));
  });

  it('asks the buyer to confirm before completing the sale', async () => {
    renderPanel({ status: 'handed_over', confirmDueAt: new Date('2026-10-08T12:00:00Z') });
    fireEvent.click(screen.getByRole('button', { name: 'It arrived healthy' }));
    expect(confirmReceived).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Yes, complete the sale' }));
    await waitFor(() => expect(confirmReceived).toHaveBeenCalledWith(3));
  });

  it('lets the buyer report a problem instead of confirming', async () => {
    renderPanel({ status: 'handed_over', confirmDueAt: new Date('2026-10-08T12:00:00Z') });
    fireEvent.click(screen.getByRole('button', { name: 'Report a problem' }));
    fireEvent.change(screen.getByLabelText("What's wrong?"), { target: { value: 'It arrived sick.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send to our team' }));
    await waitFor(() => expect(reportProblem).toHaveBeenCalledWith(3, 'It arrived sick.'));
  });

  it('uses the equipment wording on equipment orders', () => {
    renderPanel({ status: 'handed_over', confirmDueAt: new Date('2026-10-08T12:00:00Z') }, 'equipment');
    expect(screen.getByRole('button', { name: 'It arrived as described' })).toBeInTheDocument();
  });

  it('shows the server error when an action is refused', async () => {
    payOrder.mockRejectedValueOnce(new Error('This order is not waiting for payment.'));
    const { onChanged } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'Pay NT$7,500' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This order is not waiting for payment.');
    expect(onChanged).toHaveBeenCalled();
  });

  it('gives the seller no buttons while the buyer still has to pay', () => {
    renderPanel({ role: 'seller' });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
