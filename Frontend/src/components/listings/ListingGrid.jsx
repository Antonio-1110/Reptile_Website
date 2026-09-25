import './ListingGrid.css';

// `featured` uses wider cards and keeps them auto-fitting at every width (HomePage sizes its
// visible count from the 280px minimum, so keep the two in sync).
export default function ListingGrid({ variant = 'default', ref, children }) {
  return (
    <div ref={ref} className={`listing-grid${variant === 'featured' ? ' listing-grid--featured' : ''}`}>
      {children}
    </div>
  );
}
