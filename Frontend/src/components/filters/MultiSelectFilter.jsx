import FilterSection from "./FilterSection";
import "./MultiSelectFilter.css";

export default function MultiSelectFilter({ title, options, selectedValues, onChange }) {
  const toggleOption = (value) => {
    const nextValues = selectedValues.includes(value)
      ? selectedValues.filter((selectedValue) => selectedValue !== value)
      : [...selectedValues, value];

    onChange(nextValues);
  };

  return (
    <FilterSection title={title}>
      <div className="multi-select-options">
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            className={`filter-option${selectedValues.includes(option.value) ? " selected" : ""}`}
            onClick={() => toggleOption(option.value)}
            aria-pressed={selectedValues.includes(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </FilterSection>
  );
}
