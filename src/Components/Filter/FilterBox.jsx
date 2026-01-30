import FilterSection from "./FilterSection";

export default function FilterBox({ filters, setFilters }) {
  return (
    <div className="filter-box">
      <div className = "filter-box-content">
      <h2>Filters</h2>

      <FilterSection title="Location">
        <select
          value={filters.location}
          onChange={(e) =>
            setFilters({ ...filters, location: e.target.value })
          }
        >
          <option value="不限">不限</option>
          <option value="台北">台北</option>
          <option value="台中">台中</option>
          <option value="台南">台南</option>
        </select>
      </FilterSection>

      <FilterSection title="Price Range">
        <input
          type="number"
          placeholder="Min"
          value={filters.minPrice}
          onChange={(e) =>
            setFilters({ ...filters, minPrice: Number(e.target.value) })
          }
        />
        <input
          type="number"
          placeholder="Max"
          value={filters.maxPrice}
          onChange={(e) =>
            setFilters({ ...filters, maxPrice: Number(e.target.value) })
          }
        />
      </FilterSection>

      <FilterSection title="Size (cm)">
        <input
          type="number"
          placeholder="Min"
          value={filters.minSize}
          onChange={(e) =>
            setFilters({ ...filters, minSize: Number(e.target.value) })
          }
        />
        <input
          type="number"
          placeholder="Max"
          value={filters.maxSize}
          onChange={(e) =>
            setFilters({ ...filters, maxSize: Number(e.target.value) })
          }
        />
      </FilterSection>
      </div>
    </div>
  );
}
