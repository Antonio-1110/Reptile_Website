import './Skeleton.css';

// Grey placeholder block shown while content loads. Purely decorative: pair it with a text status
// (e.g. an sr-only role="status") so screen readers hear that something is loading.
export default function Skeleton({ className = '', style }) {
  return <span className={`skeleton ${className}`} style={style} aria-hidden="true" />;
}
