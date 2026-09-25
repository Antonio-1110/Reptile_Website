import FilterSection from "./FilterSection";
import "./RangeFilter.css";

export default function RangeFilter({
  title,
  min,
  max,
  rangeMin,
  rangeMax,
  step = 1,
  onMinChange,
  onMaxChange,
  allowDecimal = false,
  formatWithCommas = false,
}) {
  const valuePattern = allowDecimal ? /^\d*(\.\d?)?$/ : /^\d*$/;
  const handleInputChange = (value, onChange) => {
    const unformattedValue = value.replace(/,/g, "");
    if (valuePattern.test(unformattedValue)) onChange(unformattedValue);
  };
  const displayValue = (value) => (
    formatWithCommas && value !== "" ? Number(value).toLocaleString("en-US") : value
  );
  const handleKeyDown = (event) => {
    if (["e", "E", "+", "-"].includes(event.key)) event.preventDefault();
  };
  const clampValue = (value, onChange) => {
    if (value === "") return;

    const numericValue = Number(value.replace(/,/g, ""));
    const clampedValue = Math.min(rangeMax, Math.max(rangeMin, numericValue));
    onChange(clampedValue);
  };
  const minPlaceholderText = String(rangeMin);
  const maxPlaceholderText = String(rangeMax);

  return (
    <FilterSection title={title}>
      <div className="range-filter">
        <div className="range-filter-inputs">
          <input
            type="text"
            inputMode={allowDecimal ? "decimal" : "numeric"}
            min={rangeMin}
            max={rangeMax}
            step={step}
            value={displayValue(min)}
            placeholder={minPlaceholderText}
            onChange={(event) => handleInputChange(event.target.value, onMinChange)}
            onKeyDown={handleKeyDown}
            onBlur={(event) => clampValue(event.target.value, onMinChange)}
          />
          <input
            type="text"
            inputMode={allowDecimal ? "decimal" : "numeric"}
            min={rangeMin}
            max={rangeMax}
            step={step}
            value={displayValue(max)}
            placeholder={maxPlaceholderText}
            onChange={(event) => handleInputChange(event.target.value, onMaxChange)}
            onKeyDown={handleKeyDown}
            onBlur={(event) => clampValue(event.target.value, onMaxChange)}
          />
        </div>
      </div>
    </FilterSection>
  );
}