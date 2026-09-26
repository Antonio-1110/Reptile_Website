// Equipment categories and condition codes, matching EquipmentPost.CategoryChoices and
// ConditionChoices in backend/post/models.py. Labels: createListing.equipment.* in the locale files.
export const EQUIPMENT_CATEGORIES = [
  "enclosure",
  "heating",
  "lighting",
  "climate",
  "substrateDecor",
  "transport",
  "other",
];

export const DEFAULT_EQUIPMENT_CATEGORY = "other";

// Condition codes as the API sends them: 2 new, 1 used, 0 not functional.
export const EQUIPMENT_CONDITIONS = [2, 1, 0];

export const DEFAULT_EQUIPMENT_CONDITION = 1;
