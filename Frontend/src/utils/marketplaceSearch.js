// The marketplace search (free text + header tags) lives in the URL so it survives reloads and
// navigating from other pages: /marketplace?search=pied&species=Ball%20Pythons&genes=Pastel,Pied

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

export function buildMarketplaceUrl(term, tags) {
  const params = new URLSearchParams();
  if (term.trim()) params.set("search", term.trim());
  const species = tags.find((tag) => tag.type === "species");
  if (species) params.set("species", species.value);
  const genes = tags.filter((tag) => tag.type === "morph").map((tag) => tag.value);
  if (genes.length) params.set("genes", genes.join(","));
  const query = params.toString();
  return query ? `/marketplace?${query}` : "/marketplace";
}
