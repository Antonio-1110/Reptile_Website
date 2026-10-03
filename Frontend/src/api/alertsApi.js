import { authFetch } from "./authApi";

// The signed-in user's site alerts (price drops, saved-search matches, species reviews, auction and
// order steps). The server answers in the Accept-Language of the request, so titles follow the site
// language.
function normalizeAlert(item) {
  return {
    id: item.id,
    title: item.title,
    body: item.body,
    link: item.link,
    createdAt: new Date(item.created_at),
    isRead: item.is_read,
  };
}

export async function getAlertsPage(page = 1) {
  const payload = await authFetch(`/alerts/?page=${page}`, { method: "GET" });
  return { results: payload.results.map(normalizeAlert), hasMore: Boolean(payload.next) };
}

export async function getUnreadAlertCount() {
  const payload = await authFetch("/alerts/unread-count/", { method: "GET" });
  return payload.count;
}

export async function markAllAlertsRead() {
  return authFetch("/alerts/read-all/", { method: "POST" });
}
