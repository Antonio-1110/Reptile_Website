import { authFetch } from "./authApi";
import { getLocationCode, getLocationKey } from "../constants/locations";
import i18n from "../i18n";
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
    species: item.species_name,
    seller: item.seller_name || item.seller?.display_name || item.seller?.username,
    sellerTag: item.seller?.username,
    sellerId: item.seller_id ?? item.seller?.id,
    rating: item.seller_rating ?? item.seller?.seller_rating ?? 0,
    location: getLocationKey(item.location) || item.location,
    lifeStage: item.life_stage,
    ageYears: item.age_years,
    size: item.size_cm,
    weight: item.weight_grams,
    shippingMethods: item.shipping_methods || [],
    postedDays: item.posted_days ?? 0,
    guideNotes: item.guide_notes || "",
    gallery: item.gallery || [],
  };
}

export { isLoggedIn } from "./authApi";

async function request(path) {
  const response = await apiFetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const error = new Error(requestFailedMessage(response.status));
    error.status = response.status; // lets pages tell "not found" from a failure
    throw error;
  }
  return response.json();
}

const requestWithAuth = authFetch;
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
  return requestWithAuth("/auth/profile/", { method: "GET" });
}

// Public list of account plans with their limits (hobbyist, commercial, commercial_paid).
export async function getAccountPlans() {
  return request("/auth/plans/");
}

// Partial update of the signed-in user's profile; `fields` uses backend names (phone_number, line_id, …).
export async function updateCurrentProfile(fields) {
  return requestWithAuth("/auth/profile/", { method: "PATCH", body: JSON.stringify(fields) });
}

async function getSpeciesId(value) {
  const species = await requestAllPages("/posts/species/");
  const trimmedValue = value.trim().toLocaleLowerCase();
  const normalizedValue = trimmedValue.replace(/[^a-z0-9]/gi, "");
  const match = species.find((item) => {
    const normalizedName = item.name.trim().toLocaleLowerCase();
    return normalizedName === trimmedValue || (normalizedValue && normalizedName.replace(/[^a-z0-9]/gi, "") === normalizedValue);
  });
  if (!match) throw new Error(i18n.t("createListing.errors.unknownSpecies"));
  return match.id;
}

function listingEndpoint(category, id) {
  const base = category === "equipment" ? "/posts/equipment/" : "/posts/live-animals/";
  return id ? `${base}${id}/` : base;
}

async function buildLiveAnimalFields(formData) {
  return {
    species: await getSpeciesId(formData.species),
    sex: sexCodes[formData.sex] || formData.sex,
    genetics: formData.genetics.trim(),
    life_stage: formData.lifeStage,
    age_years: formData.ageYears === "" ? null : Number(formData.ageYears),
    weight_grams: formData.weight === "" ? null : Number(formData.weight),
    size_cm: formData.size === "" ? null : Number(formData.size),
    diets: formData.diets,
  };
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
    Object.assign(payload, await buildLiveAnimalFields(formData));
  } else {
    payload.condition = 1;
  }

  return requestWithAuth(listingEndpoint(isLiveAnimal ? "live_animal" : "equipment"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Partial update: omits gallery/image/contact_info (photos go through uploadListingPhotos, and the
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
    Object.assign(payload, await buildLiveAnimalFields(formData));
  }

  return requestWithAuth(listingEndpoint(isLiveAnimal ? "live_animal" : "equipment", id), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// Replaces a listing's photos with `files` (File objects); the one at coverIndex becomes the cover.
export async function uploadListingPhotos(id, category, files, coverIndex = 0) {
  const body = new FormData();
  files.forEach((file) => body.append("photos", file));
  body.append("cover_index", String(coverIndex));
  return requestWithAuth(`${listingEndpoint(category, id)}photos/`, { method: "POST", body });
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

// Marketplace sidebar state → query params understood by backend/post/filters.py.
function buildListingParams({ search = "", tags = [], filters = {}, seller = null }) {
  const params = new URLSearchParams();
  const set = (key, value) => {
    if (value !== "" && value != null) params.set(key, value);
  };
  set("seller", seller);
  const setList = (key, values) => {
    if (values?.length) params.set(key, values.join(","));
  };
  const setIncludeExclude = (key, values, include) => setList(include === false ? `${key}_exclude` : key, values);

  set("search", search.trim());
  set("species_name", tags.find((tag) => tag.type === "species")?.value);
  setList("genes", tags.filter((tag) => tag.type === "morph").map((tag) => tag.value));

  setList("sex", filters.sex);
  setIncludeExclude("life_stage", filters.lifeStages, filters.includeLifeStages);
  setIncludeExclude("location", filters.locations?.map(getLocationCode), filters.includeLocations);
  setIncludeExclude("diets", filters.diets, filters.includeDiets);
  setIncludeExclude("shipping", filters.shippingMethods, filters.includeShipping);
  [
    ["price", filters.minPrice, filters.maxPrice],
    ["size", filters.minSize, filters.maxSize],
    ["weight", filters.minWeight, filters.maxWeight],
    ["age", filters.minAgeYears, filters.maxAgeYears],
    ["posted_days", filters.minPostedDays, filters.maxPostedDays],
  ].forEach(([key, min, max]) => {
    set(`${key}_min`, min);
    set(`${key}_max`, max);
  });
  return params;
}

// One page of live-animal listings matching the query, plus the total match count.
export async function getListingsPage({ page = 1, ...query } = {}) {
  const params = buildListingParams(query);
  params.set("page", page);
  const payload = await request(`/posts/live-animals/?${params}`);
  return {
    results: payload.results.map(normalizeListing),
    count: payload.count,
    hasMore: Boolean(payload.next),
  };
}

// A seller's public profile (/api/sellers/<id>/): name, badges, rating, bio, listing counts.
export async function getSellerProfile(id) {
  const profile = await request(`/sellers/${id}/`);
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
  };
}

// Where a seller's name links to.
export function sellerPagePath(sellerId) {
  return `/sellers/${sellerId}`;
}

export async function getListing(id) {
  return normalizeListing(await request(`/posts/live-animals/${id}/`));
}

// What "Contact seller" would send: the signed-in user's own contact details ({contact, already_sent}).
// The seller's details are never returned; the seller gets in touch with the buyer.
export async function getContactPreview(id) {
  return requestWithAuth(`/posts/live-animals/${id}/contact/`, { method: "GET" });
}

export async function requestSellerContact(id) {
  return requestWithAuth(`/posts/live-animals/${id}/contact/`, { method: "POST" });
}

export async function reportListing(id) {
  return requestWithAuth(`/posts/live-animals/${id}/report/`, { method: "POST" });
}
