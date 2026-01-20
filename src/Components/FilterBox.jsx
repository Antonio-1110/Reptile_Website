export default function FilterBox() {
  return (
    <div className="filters">
      <div>
        <h3>Price</h3>
        <input type="range" />
      </div>

      <div style={{ marginTop: "16px" }}>
        <h3>Size</h3>
        <select>
          <option>Any</option>
          <option>Small</option>
          <option>Medium</option>
          <option>Large</option>
        </select>
      </div>
    </div>
  );
}
