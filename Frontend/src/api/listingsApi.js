import { authFetch, isLoggedIn } from "./authApi";
import { getLocationCode, getLocationKey } from "../constants/locations";
import { apiFetch, requestFailedMessage } from "./http";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const sexCodes = { male: "1.0", female: "0.1", unsexed: "unsexed" };

const sexKeys = Object.fromEntries(Object.entries(sexCodes).map(([key, code]) => [code, key]));

export function getSexKey(code) {
  return sexKeys[code] || "unsexed";
}

function normalizeListing(item) {
  return {
    ...item,
    // A listing waiting on a species review (only its owner sees it) shows the name as typed.
    species: item.species_name || item.species_review?.name,
    speciesReview: item.species_review || null,
    seller: item.seller_name || item.seller?.display_name || item.seller?.username,
    sellerTag: item.seller?.username,
    sellerId: item.seller_id ?? item.seller?.id,
    rating: item.seller_rating ?? item.seller?.seller_rating ?? 0,
    location: getLocationKey(item.location) || item.location,
    lifeStage: item.life_stage,
    ageYears: item.age_years,
    size: item.size_cm,
    weight: item.weight_grams,
    status: item.status || "available",
    shippingMethods: item.shipping_methods || [],
    isFavorite: Boolean(item.is_favorite), // saved by the signed-in viewer
    isHidden: Boolean(item.is_hidden), // hidden by moderation; only its owner (and staff) ever see it
    postedDays: item.posted_days ?? 0,
    guideNotes: item.guide_notes || "",
    gallery: item.gallery || [],
  };
}

// Equipment has no species, sex or genes; `kind` tells the card which layout to use (the API's own
// `category` field on equipment is its type, e.g. "heating").
function normalizeEquipment(item) {
  return {
    ...normalizeListing(item),
    kind: "equipment",
    equipmentCategory: item.category,
    condition: item.condition,
    genes: [],
  };
}

export { isLoggedIn } from "./authApi";

async function request(path) {
  const response = await apiFetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const error = new Error(requestFailedMessage(response.status));
    // Lets pages tell "this doesn't exist" (404) apart from "couldn't load it right now".
    error.status = response.status;
    throw error;
  }
  return response.json();
}

const requestWithAuth = authFetch;

// Public listing reads, sent with the viewer's token when there is one so `is_favorite` is theirs. A
// token that can't be refreshed any more mustn't break a public page, so a 401 retries anonymously.
async function readListings(path) {
  try {
    return await authFetch(path, { method: "GET" });
  } catch (error) {
    if (error.status === 401) return request(path);
    throw error;
  }
}
const requestWithAuthGet = (path) => authFetch(path, { method: "GET" });

// List endpoints are paginated (DRF PAGE_SIZE); the UI filters client-side, so it needs every page.
async function requestAllPages(path, fetchPage = request) {
  const results = [];
  for (let page = 1; ; page += 1) {
    const payload = await fetchPage(`${path}?page=${page}`);
    if (!Array.isArray(payload.results)) return payload;
    results.push(...payload.results);
    if (!payload.next) return results;
  }
}

export async function getCurrentProfile() {
  return requestWithAuth("/v1/auth/profile/", { method: "GET" });
}

// Public list of account plans with their limits (hobbyist, commercial, commercial_paid).
export async function getAccountPlans() {
  return request("/v1/auth/plans/");
}

// Partial update of the signed-in user's profile; `fields` uses backend names (phone_number, line_id, …).
export async function updateCurrentProfile(fields) {
  return requestWithAuth("/v1/auth/profile/", { method: "PATCH", body: JSON.stringify(fields) });
}

// The species list the editor suggests from: [{ id, name, aliases }].
export async function getSpecies() {
  return requestAllPages("/posts/species/");
}

function listingEndpoint(category, id) {
  const base = category === "equipment" ? "/posts/equipment/" : "/posts/live-animals/";
  return id ? `${base}${id}/` : base;
}

// A species picked from the list is sent by id; anything typed is sent as written, and the server
// either recognises it (a species name or alias) or holds the listing for a species review.
function buildLiveAnimalFields(formData) {
  return {
    ...(formData.speciesId ? { species: formData.speciesId } : { requested_species: formData.species.trim() }),
    sex: sexCodes[formData.sex] || formData.sex,
    genetics: formData.genetics.trim(),
    life_stage: formData.lifeStage,
    age_years: formData.ageYears === "" ? null : Number(formData.ageYears),
    weight_grams: formData.weight === "" ? null : Number(formData.weight),
    size_cm: formData.size === "" ? null : Number(formData.size),
    diets: formData.diets,
  };
}

function buildEquipmentFields(formData) {
  return { category: formData.equipmentCategory, condition: Number(formData.condition) };
}

export async function createListing(formData) {
  const isLiveAnimal = formData.category === "live_animal";
  const payload = {
    title: formData.title.trim(),
    description: formData.description.trim(),
    price: formData.price === "" ? null : Number(formData.price),
    location: getLocationCode(formData.location) || formData.location,
    contact_info: {},
    shipping_methods: formData.shippingMethods,
  };

  if (isLiveAnimal) {
    Object.assign(payload, buildLiveAnimalFields(formData));
  } else {
    Object.assign(payload, buildEquipmentFields(formData));
  }

  return requestWithAuth(listingEndpoint(isLiveAnimal ? "live_animal" : "equipment"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Partial update: omits gallery/image/contact_info (photos go through saveListingPhotos, and the
// form has no contact controls yet), so editing a listing can't wipe out existing media or contact details.
export async function updateListing(id, formData) {
  const isLiveAnimal = formData.category === "live_animal";
  const payload = {
    title: formData.title.trim(),
    description: formData.description.trim(),
    price: formData.price === "" ? null : Number(formData.price),
    location: getLocationCode(formData.location) || formData.location,
    shipping_methods: formData.shippingMethods,
  };

  if (isLiveAnimal) {
    Object.assign(payload, buildLiveAnimalFields(formData));
  } else {
    Object.assign(payload, buildEquipmentFields(formData));
  }

  return requestWithAuth(listingEndpoint(isLiveAnimal ? "live_animal" : "equipment", id), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// Sets a listing's photos to `items`, cover first: { url } keeps one of its current photos, { file }
// uploads a new one. Current photos left out are removed (see ListingPhotoUploadSerializer).
export async function saveListingPhotos(id, category, items) {
  const body = new FormData();
  let uploads = 0;
  const order = items.map((item) => {
    if (item.url) return item.url;
    body.append("photos", item.file);
    uploads += 1;
    return `new:${uploads - 1}`;
  });
  body.append("order", JSON.stringify(order));
  return requestWithAuth(`${listingEndpoint(category, id)}photos/`, { method: "POST", body });
}

// status: "available", "reserved" or "sold" (sold listings leave the marketplace but keep their page).
export async function updateListingStatus(id, category, status) {
  return requestWithAuth(listingEndpoint(category, id), { method: "PATCH", body: JSON.stringify({ status }) });
}

export async function deleteListing(id, category) {
  return requestWithAuth(listingEndpoint(category, id), { method: "DELETE" });
}

export async function getRawListing(id, category) {
  return requestWithAuth(listingEndpoint(category, id), { method: "GET" });
}

export async function getMyListings() {
  const [liveAnimals, equipment] = await Promise.all([
    requestAllPages("/posts/live-animals/mine/", requestWithAuthGet),
    requestAllPages("/posts/equipment/mine/", requestWithAuthGet),
  ]);
  const liveResults = liveAnimals.map((item) => ({ ...item, category: "live_animal" }));
  const equipmentResults = equipment.map((item) => ({ ...item, category: "equipment" }));
  return [...liveResults, ...equipmentResults].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

// Marketplace sidebar state → query params understood by backend/post/filters.py. Only the filters
// that exist for the chosen category are sent; the others keep their values for switching back.
function buildListingParams({ category = "live_animal", search = "", tags = [], filters = {}, seller = null }) {
  const params = new URLSearchParams();
  const set = (key, value) => {
    if (value !== "" && value != null) params.set(key, value);
  };
  set("seller", seller);
  const setList = (key, values) => {
    if (values?.length) params.set(key, values.join(","));
  };
  const setIncludeExclude = (key, values, include) => setList(include === false ? `${key}_exclude` : key, values);

  const ranges = [
    ["price", filters.minPrice, filters.maxPrice],
    ["posted_days", filters.minPostedDays, filters.maxPostedDays],
  ];
  set("search", search.trim());
  setIncludeExclude("location", filters.locations?.map(getLocationCode), filters.includeLocations);
  setIncludeExclude("shipping", filters.shippingMethods, filters.includeShipping);

  if (category === "equipment") {
    setList("category", filters.equipmentTypes);
    setList("condition", filters.conditions);
  } else {
    // Species and morph tags from the header only mean something for animals.
    set("species_name", tags.find((tag) => tag.type === "species")?.value);
    setList("genes", tags.filter((tag) => tag.type === "morph").map((tag) => tag.value));
    setList("sex", filters.sex);
    setIncludeExclude("life_stage", filters.lifeStages, filters.includeLifeStages);
    setIncludeExclude("diets", filters.diets, filters.includeDiets);
    ranges.push(
      ["size", filters.minSize, filters.maxSize],
      ["weight", filters.minWeight, filters.maxWeight],
      ["age", filters.minAgeYears, filters.maxAgeYears],
    );
  }
  ranges.forEach(([key, min, max]) => {
    set(`${key}_min`, min);
    set(`${key}_max`, max);
  });
  return params;
}

// The listing API query for the marketplace's current search and filters (what a saved search stores).
export function listingQueryString(query) {
  return buildListingParams(query).toString();
}

// The reverse of buildListingParams: a stored query string (a saved search) → the marketplace's
// search text, header tags and sidebar filters, so the search can be opened and edited. Only the
// filters present in the query are returned; the caller fills in the rest.
const RANGE_FILTERS = [
  ["price", "minPrice", "maxPrice"],
  ["posted_days", "minPostedDays", "maxPostedDays"],
  ["size", "minSize", "maxSize"],
  ["weight", "minWeight", "maxWeight"],
  ["age", "minAgeYears", "maxAgeYears"],
];
const LIST_FILTERS = [
  ["sex", "sex"],
  ["category", "equipmentTypes"],
  ["condition", "conditions"],
];
const INCLUDE_EXCLUDE_FILTERS = [
  ["location", "locations", "includeLocations", getLocationKey],
  ["shipping", "shippingMethods", "includeShipping"],
  ["life_stage", "lifeStages", "includeLifeStages"],
  ["diets", "diets", "includeDiets"],
];

export function parseListingQuery(queryString) {
  const params = new URLSearchParams(queryString);
  const list = (key) => (params.get(key) || "").split(",").filter(Boolean);
  const filters = {};
  RANGE_FILTERS.forEach(([key, minName, maxName]) => {
    if (params.has(`${key}_min`)) filters[minName] = params.get(`${key}_min`);
    if (params.has(`${key}_max`)) filters[maxName] = params.get(`${key}_max`);
  });
  LIST_FILTERS.forEach(([key, name]) => {
    if (params.has(key)) filters[name] = list(key);
  });
  INCLUDE_EXCLUDE_FILTERS.forEach(([key, name, includeName, toUiValue = (value) => value]) => {
    const exclude = params.has(`${key}_exclude`);
    if (!exclude && !params.has(key)) return;
    filters[name] = list(exclude ? `${key}_exclude` : key).map(toUiValue).filter(Boolean);
    filters[includeName] = !exclude;
  });
  const species = params.get("species_name");
  return {
    search: params.get("search") || "",
    tags: [
      ...(species ? [{ type: "species", value: species }] : []),
      ...list("genes").map((value) => ({ type: "morph", value })),
    ],
    filters,
  };
}

// The signed-in user's saved searches ({ id, name, query, createdAt }), newest first.
export async function getSavedSearches() {
  const payload = await requestWithAuth("/posts/saved-searches/", { method: "GET" });
  return payload.results.map((item) => ({ id: item.id, name: item.name, query: item.query, createdAt: new Date(item.created_at) }));
}

// Saves a search so the user is emailed about new matches; name defaults to the search text.
export async function createSavedSearch(query, name = "") {
  return requestWithAuth("/posts/saved-searches/", { method: "POST", body: JSON.stringify({ query, name }) });
}

// Renames a saved search and/or replaces its query (`changes`: { name?, query? }).
export async function updateSavedSearch(id, changes) {
  return requestWithAuth(`/posts/saved-searches/${id}/`, { method: "PATCH", body: JSON.stringify(changes) });
}

export async function deleteSavedSearch(id) {
  return requestWithAuth(`/posts/saved-searches/${id}/`, { method: "DELETE" });
}

// One page of listings (live animals or equipment, per query.category) matching the query, plus the
// total match count.
export async function getListingsPage({ page = 1, ...query } = {}) {
  const isEquipment = query.category === "equipment";
  const params = buildListingParams(query);
  params.set("page", page);
  const payload = await readListings(`${listingEndpoint(isEquipment ? "equipment" : "live_animal")}?${params}`);
  return {
    results: payload.results.map(isEquipment ? normalizeEquipment : normalizeListing),
    count: payload.count,
    hasMore: Boolean(payload.next),
  };
}

// A seller's public profile (/api/sellers/<id>/): name, badges, rating, bio, listing counts.
export async function getSellerProfile(id) {
  // Sent with the viewer's token when signed in, so can_review / my_review are theirs.
  const profile = isLoggedIn() ? await requestWithAuth(`/sellers/${id}/`, { method: "GET" }) : await request(`/sellers/${id}/`);
  return {
    id: profile.id,
    username: profile.username,
    displayName: profile.display_name,
    isCommercial: profile.is_commercial,
    verified: profile.verified_seller,
    rating: profile.seller_rating,
    totalReviews: profile.total_reviews,
    bio: profile.bio || "",
    memberSince: new Date(profile.member_since),
    liveAnimalCount: profile.live_animal_count,
    equipmentCount: profile.equipment_count,
    canReview: Boolean(profile.can_review),
    myReview: profile.my_review ? normalizeReview(profile.my_review) : null,
  };
}

function normalizeReview(review) {
  return {
    id: review.id,
    reviewer: review.reviewer,
    rating: review.rating,
    comment: review.comment || "",
    createdAt: new Date(review.created_at),
    isMine: Boolean(review.is_mine),
  };
}

// One page of a seller's reviews, newest first.
export async function getSellerReviews(sellerId, page = 1) {
  const path = `/sellers/${sellerId}/reviews/?page=${page}`;
  const payload = isLoggedIn() ? await requestWithAuth(path, { method: "GET" }) : await request(path);
  return { results: payload.results.map(normalizeReview), count: payload.count, hasMore: Boolean(payload.next) };
}

// Write or update the signed-in user's review of a seller.
export async function saveSellerReview(sellerId, rating, comment) {
  return normalizeReview(await requestWithAuth(`/sellers/${sellerId}/reviews/`, {
    method: "POST",
    body: JSON.stringify({ rating, comment }),
  }));
}

export async function deleteSellerReview(sellerId) {
  return requestWithAuth(`/sellers/${sellerId}/reviews/`, { method: "DELETE" });
}

// Where a seller's name links to.
export function sellerPagePath(sellerId) {
  return `/sellers/${sellerId}`;
}

// Save (on = true) or unsave a listing for the signed-in user. Returns the new state.
export async function setFavorite(id, category, on) {
  const result = await requestWithAuth(`${listingEndpoint(category, id)}favorite/`, { method: on ? "POST" : "DELETE" });
  return Boolean(result?.is_favorite);
}

// One page of the signed-in user's saved animals, most recently saved first.
export async function getFavoritesPage(page = 1) {
  const payload = await requestWithAuth(`/posts/live-animals/favorites/?page=${page}`, { method: "GET" });
  return { results: payload.results.map(normalizeListing), count: payload.count, hasMore: Boolean(payload.next) };
}

// `category` is "live_animal" (default) or "equipment" in the functions below.
export async function getListing(id, category = "live_animal") {
  const item = await readListings(listingEndpoint(category, id));
  return category === "equipment" ? normalizeEquipment(item) : normalizeListing(item);
}

// What "Contact seller" would send: the signed-in user's own contact details ({contact, already_sent}).
// The seller's details are never returned; the seller gets in touch with the buyer.
export async function getContactPreview(id, category = "live_animal") {
  return requestWithAuth(`${listingEndpoint(category, id)}contact/`, { method: "GET" });
}

export async function requestSellerContact(id, category = "live_animal") {
  return requestWithAuth(`${listingEndpoint(category, id)}contact/`, { method: "POST" });
}

export async function reportListing(id, category = "live_animal") {
  return requestWithAuth(`${listingEndpoint(category, id)}report/`, { method: "POST" });
}

// Where a listing's public page is: animals at /posts/:id, equipment at /equipment/:id.
export function listingPagePath(id, category = "live_animal") {
  return category === "equipment" ? `/equipment/${id}` : `/posts/${id}`;
}
