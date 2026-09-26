import './BackLink.css';
import { Link } from 'react-router';

// The "back to …" link at the top left of a page, above its heading: one look and one place on every
// page that has one. The destination is fixed (not the browser history) so the label can name it.
export default function BackLink({ to, children, className = '' }) {
  return (
    <Link to={to} className={`back-link${className ? ` ${className}` : ''}`}>
      <span aria-hidden="true">←</span> {children}
    </Link>
  );
}
