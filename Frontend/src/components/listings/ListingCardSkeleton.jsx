import './ListingCard.css';
import './ListingCardSkeleton.css';
import Skeleton from '../ui/Skeleton';

// Same footprint as ListingCard, so the grid doesn't jump when the real cards arrive.
export default function ListingCardSkeleton() {
  return (
    <div className="card-container listing-card-skeleton" aria-hidden="true">
      <Skeleton className="listing-card-skeleton-image" />
      <div className="card-content">
        <Skeleton className="listing-card-skeleton-line" style={{ width: '80%' }} />
        <Skeleton className="listing-card-skeleton-line" style={{ width: '45%' }} />
        <Skeleton className="listing-card-skeleton-line" style={{ width: '60%' }} />
        <Skeleton className="listing-card-skeleton-line" style={{ width: '35%' }} />
      </div>
    </div>
  );
}
