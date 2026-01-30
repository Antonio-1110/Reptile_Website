export default function FilterSection({ title, children }) {
  return (
    <div className="filter-section">
      <h4>{title}</h4>
      <div className="filter-controls">
        {children}
      </div>
    </div>
  );
}