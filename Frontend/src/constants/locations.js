// Single source of truth for listing locations. `code` is what the backend stores
// (BasePost.Locations in backend/post/models.py); `key` is what the UI uses and what
// the `locations.*` translation keys are named after. Order is the display order.
export const LOCATIONS = [
  { key: "taipei", code: "TPE" },
  { key: "newTaipei", code: "NWT" },
  { key: "taoyuan", code: "TYN" },
  { key: "taichung", code: "TXG" },
  { key: "tainan", code: "TNN" },
  { key: "kaohsiung", code: "KHH" },
  { key: "keelung", code: "KEE" },
  { key: "hsinchuCity", code: "HSZ" },
  { key: "chiayiCity", code: "CYI" },
  { key: "hsinchuCounty", code: "HSQ" },
  { key: "miaoli", code: "MIA" },
  { key: "changhua", code: "CHA" },
  { key: "nantou", code: "NAN" },
  { key: "yunlin", code: "YUN" },
  { key: "chiayiCounty", code: "CYQ" },
  { key: "pingtung", code: "PIF" },
  { key: "yilan", code: "ILA" },
  { key: "hualien", code: "HUA" },
  { key: "taitung", code: "TTT" },
  { key: "penghu", code: "PEN" },
  { key: "kinmen", code: "KIN" },
  { key: "lienchiang", code: "LIE" },
  { key: "other", code: "OTH" },
];

export const LOCATION_KEYS = LOCATIONS.map(({ key }) => key);

const keyByCode = Object.fromEntries(LOCATIONS.map(({ key, code }) => [code, key]));
const codeByKey = Object.fromEntries(LOCATIONS.map(({ key, code }) => [key, code]));

export function getLocationKey(code) {
  return keyByCode[code] || "";
}

export function getLocationCode(key) {
  return codeByKey[key] || "";
}

// Translated display name for a location key; falls back to the raw value for unknown keys.
export function getLocationLabel(t, key) {
  return codeByKey[key] ? t(`locations.${key}`) : key;
}
