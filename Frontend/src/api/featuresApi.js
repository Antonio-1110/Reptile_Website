import { API_URL, apiFetch, requestFailedMessage } from "./http";

// Which parts of the site staff have switched on, e.g. { auctions: false } (backend features app).
export async function getFeatures() {
  const response = await apiFetch(`${API_URL}/features/`);
  if (!response.ok) throw new Error(requestFailedMessage(response.status));
  return response.json();
}
