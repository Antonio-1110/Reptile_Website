// Backend species names (post.Species.name) → translation keys. The species list itself is seeded by
// backend/post/migrations/0018_seed_species_catalog.py.
const SPECIES_KEYS = {
  "Ball Pythons": "species.ballPythons",
  "Crested Geckos": "species.crestedGeckos",
  "Leopard Geckos": "species.leopardGeckos",
  "Corn Snakes": "species.cornSnakes",
  "Bearded Dragons": "species.beardedDragons",
  "紅面蛋": "species.redCheekedMudTurtles",
  "鑽紋龜": "species.diamondbackTerrapins",
  "Western Hognose Snakes": "speciesCatalog.westernHognoseSnakes",
  "California Kingsnakes": "speciesCatalog.californiaKingsnakes",
  "Milk Snakes": "speciesCatalog.milkSnakes",
  "Boa Constrictors": "speciesCatalog.boaConstrictors",
  "Carpet Pythons": "speciesCatalog.carpetPythons",
  "Green Tree Pythons": "speciesCatalog.greenTreePythons",
  "Blood Pythons": "speciesCatalog.bloodPythons",
  "Rosy Boas": "speciesCatalog.rosyBoas",
  "Kenyan Sand Boas": "speciesCatalog.kenyanSandBoas",
  "Gargoyle Geckos": "speciesCatalog.gargoyleGeckos",
  "African Fat-tailed Geckos": "speciesCatalog.fatTailedGeckos",
  "Tokay Geckos": "speciesCatalog.tokayGeckos",
  "New Caledonian Giant Geckos": "speciesCatalog.giantGeckos",
  "Blue-tongued Skinks": "speciesCatalog.blueTonguedSkinks",
  "Veiled Chameleons": "speciesCatalog.veiledChameleons",
  "Panther Chameleons": "speciesCatalog.pantherChameleons",
  "Argentine Tegus": "speciesCatalog.argentineTegus",
  "Savannah Monitors": "speciesCatalog.savannahMonitors",
  "Uromastyx": "speciesCatalog.uromastyx",
  "Common Musk Turtles": "speciesCatalog.commonMuskTurtles",
  "Sulcata Tortoises": "speciesCatalog.sulcataTortoises",
  "Russian Tortoises": "speciesCatalog.russianTortoises",
  "Hermann's Tortoises": "speciesCatalog.hermannsTortoises",
  "Leopard Tortoises": "speciesCatalog.leopardTortoises",
};

// Translated species name; unknown species (added in the admin later) fall back to their stored name.
export function getSpeciesLabel(t, name) {
  const key = SPECIES_KEYS[name];
  return key ? t(key) : name;
}

// Same rule as the backend (post/species.py normalize): case, spaces and punctuation don't make a
// different species, so "Ball-python" and "ball python" are the same name.
export function normalizeSpeciesName(name) {
  return (name || "").toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
}

// Every name that picks a species: its label in the UI language, its stored name and its aliases.
function speciesTerms(t, species) {
  return [getSpeciesLabel(t, species.name), species.name, ...(species.aliases || [])];
}

// Species from /posts/species/ whose names contain `text`, and the one it names exactly (or null).
// An exact match needs no review: the server picks it from the typed name too.
export function matchSpecies(t, speciesList, text) {
  const key = normalizeSpeciesName(text);
  if (!key) return { matches: [], exact: null };
  const matches = speciesList.filter((species) => speciesTerms(t, species).some((term) => normalizeSpeciesName(term).includes(key)));
  const exact = matches.find((species) => speciesTerms(t, species).some((term) => normalizeSpeciesName(term) === key)) || null;
  return { matches, exact };
}
