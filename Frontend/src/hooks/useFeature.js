import { useSyncExternalStore } from "react";
import { getFeatures } from "../api/featuresApi";

// The feature switches, fetched once per page load and shared by every component that asks.
// The backend enforces them; the frontend only hides what's switched off.
let features = null;
let loading = null;
const listeners = new Set();

function publish(value) {
  features = value;
  listeners.forEach((listener) => listener());
}

function load() {
  if (features || loading) return;
  loading = getFeatures()
    .then(publish)
    // If the switches can't be read, switchable parts stay hidden rather than offering things the
    // backend may refuse.
    .catch(() => publish({}))
    .finally(() => { loading = null; });
}

function subscribe(listener) {
  listeners.add(listener);
  load();
  return () => listeners.delete(listener);
}

// Whether a switch (e.g. "auctions") is on: true or false, or undefined while the switches load.
export default function useFeature(name) {
  const state = useSyncExternalStore(subscribe, () => features);
  return state ? Boolean(state[name]) : undefined;
}

// Tests set the switches directly; null makes the next component fetch them.
export function setFeatures(value) {
  loading = null;
  publish(value);
}
