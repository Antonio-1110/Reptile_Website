import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createListing, getListingsPage, getSexKey, listingQueryString, parseListingQuery } from './listingsApi';

// A fetch stand-in that records the URL and answers with one page of API results.
function mockFetch(results = [], { next = null, count = results.length } = {}) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ results, count, next }), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const requestedParams = (fetchMock) => new URL(fetchMock.mock.calls[0][0]).searchParams;

describe('getListingsPage: marketplace filters → API query', () => {
  beforeEach(() => mockFetch());
  afterEach(() => vi.unstubAllGlobals());

  it('sends only the filters that are set, with backend names and codes', async () => {
    const fetchMock = mockFetch();
    await getListingsPage({
      search: '  pied ',
      tags: [{ type: 'species', value: 'Ball Pythons' }, { type: 'morph', value: 'Pastel' }, { type: 'morph', value: 'Pied' }],
      filters: {
        sex: ['1.0', 'unsexed'],
        lifeStages: ['adult'], includeLifeStages: true,
        locations: ['taipei'], includeLocations: false,
        diets: [], shippingMethods: ['shipping'], includeShipping: true,
        minPrice: '1000', maxPrice: '', minWeight: '', maxWeight: '500',
      },
      page: 2,
    });
    const params = requestedParams(fetchMock);
    expect(Object.fromEntries(params)).toEqual({
      search: 'pied',
      species_name: 'Ball Pythons',
      genes: 'Pastel,Pied',
      sex: '1.0,unsexed',
      life_stage: 'adult',
      location_exclude: 'TPE', // "exclude" mode flips the parameter name; UI keys become backend codes
      shipping: 'shipping',
      price_min: '1000',
      weight_max: '500',
      page: '2',
    });
  });

  it('asks for the first page with no filters at all', async () => {
    const fetchMock = mockFetch();
    await getListingsPage({});
    expect(Object.fromEntries(requestedParams(fetchMock))).toEqual({ page: '1' });
  });

  it('asks the versioned API for the chosen listing type', async () => {
    const fetchMock = mockFetch();
    await getListingsPage({ category: 'equipment' });
    expect(new URL(fetchMock.mock.calls[0][0]).pathname).toBe('/api/v1/posts/equipment/');
  });

  it('maps API fields to the names the UI uses', async () => {
    mockFetch([{
      id: 7, title: 'Pied', species_name: 'Ball Pythons', location: 'TPE', life_stage: 'adult', age_years: 2,
      size_cm: 90, weight_grams: 800, shipping_methods: ['shipping'], posted_days: 3, genes: ['Pied'],
      seller: { id: 3, username: 'apex', display_name: 'Apex Exotics', seller_rating: 4.9 },
    }], { next: 'http://x/?page=2', count: 30 });
    const { results, count, hasMore } = await getListingsPage({});
    expect(count).toBe(30);
    expect(hasMore).toBe(true);
    expect(results[0]).toMatchObject({
      species: 'Ball Pythons', location: 'taipei', lifeStage: 'adult', ageYears: 2, size: 90, weight: 800,
      shippingMethods: ['shipping'], postedDays: 3, seller: 'Apex Exotics', sellerTag: 'apex', sellerId: 3, rating: 4.9,
    });
  });
});

describe('getSexKey', () => {
  it('turns API sex codes into UI keys, defaulting to unsexed', () => {
    expect(getSexKey('1.0')).toBe('male');
    expect(getSexKey('0.1')).toBe('female');
    expect(getSexKey('unsexed')).toBe('unsexed');
    expect(getSexKey(undefined)).toBe('unsexed');
  });
});

describe('createListing: species', () => {
  afterEach(() => vi.unstubAllGlobals());

  const form = {
    title: ' Skink ', description: 'd', price: '100', category: 'live_animal', sex: 'unsexed', genetics: '',
    lifeStage: 'adult', ageYears: '', weight: '', size: '', diets: [], location: 'taipei', shippingMethods: [],
  };
  const sentBody = async (fields) => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 1 }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);
    await createListing({ ...form, ...fields });
    return JSON.parse(fetchMock.mock.calls[0][1].body);
  };

  it('sends a species picked from the list by id', async () => {
    const body = await sentBody({ species: '球蟒', speciesId: 3 });
    expect(body.species).toBe(3);
    expect(body).not.toHaveProperty('requested_species');
  });

  it('sends a typed species as written, for the server to match or review', async () => {
    const body = await sentBody({ species: ' Blue Tongue Skink ', speciesId: null });
    expect(body.requested_species).toBe('Blue Tongue Skink');
    expect(body).not.toHaveProperty('species');
  });
});

describe('parseListingQuery: a saved search → marketplace search and filters', () => {
  it('reads back what listingQueryString wrote', () => {
    const query = {
      search: 'pied',
      tags: [{ type: 'species', value: 'Ball Pythons' }, { type: 'morph', value: 'Pastel' }],
      filters: {
        sex: ['0.1'],
        locations: ['taipei', 'taichung'], includeLocations: false,
        lifeStages: ['adult'], includeLifeStages: true,
        minPrice: '1000', maxWeight: '500', minAgeYears: '1.5',
      },
    };
    const parsed = parseListingQuery(listingQueryString(query));
    expect(parsed.search).toBe('pied');
    expect(parsed.tags).toEqual(query.tags);
    expect(parsed.filters).toEqual(query.filters);
  });

  it('returns no filters for an empty query', () => {
    expect(parseListingQuery('')).toEqual({ search: '', tags: [], filters: {} });
  });
});
