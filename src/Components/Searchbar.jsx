export default function Searchbar({ onSearch }) {
  return (
    <div className="csfloat-topbar">
      <div className="csfloat-search-wrap">
        <input
          type="text"
          className="csfloat-search"
          placeholder="Search reptiles…"
          onChange={(e) => onSearch?.(e.target.value)}
        />
      </div>
    </div>
  );
}
