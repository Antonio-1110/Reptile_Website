import * as Sentry from "@sentry/react";

// Error monitoring only: no tracing or session replay (they eat the free quota, and replay records
// what visitors do on screen). Nothing is sent unless VITE_SENTRY_DSN is set at build time.
const DSN = import.meta.env.VITE_SENTRY_DSN;

// Email links put one-time tokens in the query string (/reset-password?uid=…&token=…), and the
// hash can carry state too, so neither may leave the browser in an error report.
export function scrubUrl(url) {
  if (typeof url !== "string") return url;
  return url.split(/[?#]/, 1)[0];
}

export function scrubEvent(event) {
  if (event.request) {
    event.request.url = scrubUrl(event.request.url);
    delete event.request.query_string;
    delete event.request.cookies;
    if (event.request.headers?.Referer) {
      event.request.headers.Referer = scrubUrl(event.request.headers.Referer);
    }
  }
  return event;
}

export function scrubBreadcrumb(breadcrumb) {
  const data = breadcrumb.data;
  if (data) {
    for (const key of ["url", "from", "to"]) {
      if (key in data) data[key] = scrubUrl(data[key]);
    }
  }
  return breadcrumb;
}

export const sentryEnabled = Boolean(DSN);

export function initSentry() {
  if (!sentryEnabled) return;
  Sentry.init({
    dsn: DSN,
    environment: import.meta.env.MODE,
    sendDefaultPii: false,
    beforeSend: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  });
}

// Options for createRoot so React's own error hooks report to Sentry; empty when it's off, which
// keeps React's default console logging.
export function rootErrorOptions() {
  if (!sentryEnabled) return {};
  return {
    onUncaughtError: Sentry.reactErrorHandler(),
    onCaughtError: Sentry.reactErrorHandler(),
    onRecoverableError: Sentry.reactErrorHandler(),
  };
}
