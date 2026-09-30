import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import useFeature, { setFeatures } from './useFeature';

describe('useFeature', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('is unknown while the switches load, then follows them', async () => {
    setFeatures(null);
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ auctions: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useFeature('auctions'));
    expect(result.current).toBeUndefined();
    await waitFor(() => expect(result.current).toBe(true));
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/v1\/features\/$/);
  });

  it('asks the server once for every component', async () => {
    setFeatures(null);
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ auctions: false }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const first = renderHook(() => useFeature('auctions'));
    const second = renderHook(() => useFeature('auctions'));
    await waitFor(() => expect(second.result.current).toBe(false));
    expect(first.result.current).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps switchable parts hidden when the switches cannot be read', async () => {
    setFeatures(null);
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline'); }));
    const { result } = renderHook(() => useFeature('auctions'));
    await waitFor(() => expect(result.current).toBe(false));
  });

  it('updates components when the switches change', () => {
    setFeatures({ auctions: false });
    const { result } = renderHook(() => useFeature('auctions'));
    expect(result.current).toBe(false);
    act(() => setFeatures({ auctions: true }));
    expect(result.current).toBe(true);
  });
});
