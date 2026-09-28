// The page to go to after signing in, from ?next=. Only same-site relative paths are allowed, so the
// link can't send people off-site.
export function safeNextPath(search, fallback = '/marketplace') {
  const next = new URLSearchParams(search).get('next') || '';
  return next.startsWith('/') && !next.startsWith('//') ? next : fallback;
}
