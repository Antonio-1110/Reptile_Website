const ANIMAL_FILTERS = [
  ["sex"], ["lifeStages"], ["diets"], ["shippingMethods"], ["locations"],
  ["minAgeYears", "maxAgeYears"], ["minWeight", "maxWeight"], ["minPostedDays", "maxPostedDays"],
  ["minPrice", "maxPrice"], ["minSize", "maxSize"],
];
const EQUIPMENT_FILTERS = [
  ["equipmentTypes"], ["conditions"], ["shippingMethods"], ["locations"],
  ["minPostedDays", "maxPostedDays"], ["minPrice", "maxPrice"],
];
const isSet = (value) => (Array.isArray(value) ? value.length > 0 : value !== "" && value != null);

// How many of the filters shown for this category narrow the results (a range counts once).
export function countActiveFilters(category, filters) {
  const groups = category === "equipment" ? EQUIPMENT_FILTERS : ANIMAL_FILTERS;
  return groups.filter((keys) => keys.some((key) => isSet(filters[key]))).length;
}
