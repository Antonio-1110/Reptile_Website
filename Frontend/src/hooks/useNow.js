import { useEffect, useState } from "react";

// The current time, refreshed every `intervalMs`. Use it once per page and pass it down, so a page of
// countdowns shares one timer and they all tick together.
export default function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}
