// Backend species names (post.Species.name) → `species.*` translation keys.
const SPECIES_KEYS = {
  "Ball Pythons": "ballPythons",
  "Crested Geckos": "crestedGeckos",
  "Leopard Geckos": "leopardGeckos",
  "Corn Snakes": "cornSnakes",
  "Bearded Dragons": "beardedDragons",
  "紅面蛋": "redCheekedMudTurtles",
  "鑽紋龜": "diamondbackTerrapins",
};

// Translated species name; unknown species (added in the admin later) fall back to their stored name.
export function getSpeciesLabel(t, name) {
  const key = SPECIES_KEYS[name];
  return key ? t(`species.${key}`) : name;
}
