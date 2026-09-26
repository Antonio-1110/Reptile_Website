// The marketplace search (free text + header tags) and what's being browsed (animals or equipment)
// live in the URL so they survive reloads and navigating from other pages:
// /marketplace?search=pied&species=Ball%20Pythons&genes=Pastel,Pied, /marketplace?category=equipment

export const MARKETPLACE_CATEGORIES = ["live_animal", "equipment"];

export function readMarketplaceCategory(search = window.location.search) {
  const category = new URLSearchParams(search).get("category");
  return MARKETPLACE_CATEGORIES.includes(category) ? category : "live_animal";
}

// Same URL with only the category changed (live animals are the default, so they leave no param).
export function withMarketplaceCategory(category, search = window.location.search) {
  const params = new URLSearchParams(search);
  if (category === "live_animal") params.delete("category");
  else params.set("category", category);
  const query = params.toString();
  return query ? `/marketplace?${query}` : "/marketplace";
}

export function readMarketplaceSearch(search = window.location.search) {
  const params = new URLSearchParams(search);
  const species = params.get("species");
  const genes = (params.get("genes") || "").split(",").filter(Boolean);
  return {
    term: (params.get("search") || "").trim(),
    tags: [
      ...(species ? [{ type: "species", value: species }] : []),
      ...genes.map((value) => ({ type: "morph", value })),
    ],
  };
}

export function buildMarketplaceUrl(term, tags, category = "live_animal") {
  const params = new URLSearchParams();
  if (category !== "live_animal") params.set("category", category);
  if (term.trim()) params.set("search", term.trim());
  const species = tags.find((tag) => tag.type === "species");
  if (species) params.set("species", species.value);
  const genes = tags.filter((tag) => tag.type === "morph").map((tag) => tag.value);
  if (genes.length) params.set("genes", genes.join(","));
  const query = params.toString();
  return query ? `/marketplace?${query}` : "/marketplace";
}
