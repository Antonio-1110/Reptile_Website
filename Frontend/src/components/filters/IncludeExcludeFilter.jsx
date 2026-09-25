import { useState } from "react";
import { useTranslation } from "react-i18next";
import FilterSection from "./FilterSection";
import "./IncludeExcludeFilter.css";

export default function IncludeExcludeFilter({
  title,
  includeLabel,
  options,
  selectedValues,
  onSelectionChange,
}) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [isIncluded, setIsIncluded] = useState(true);

  const toggleSelection = (value) => {
    const nextValues = selectedValues.includes(value)
      ? selectedValues.filter((selectedValue) => selectedValue !== value)
      : [...selectedValues, value];

    onSelectionChange(nextValues, isIncluded);
  };

  const setIncludeMode = (include) => {
    setIsIncluded(include);
    onSelectionChange(selectedValues, include);
  };

  return (
    <FilterSection title={title}>
      <div className="include-exclude-filter">
        <button
          type="button"
          className={`include-exclude-trigger ${isIncluded ? "selected" : ""}`}
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
        >
          {includeLabel}
          <span aria-hidden="true">{isOpen ? "▲" : "▼"}</span>
        </button>

        {isOpen && (
          <div className="include-exclude-popover">
            <div className="include-exclude-modes">
              <button
                type="button"
                className={`filter-option${isIncluded ? " selected" : ""}`}
                onClick={() => setIncludeMode(true)}
              >
                {t("filters.include")}
              </button>
              <button
                type="button"
                className={`filter-option${!isIncluded ? " selected" : ""}`}
                onClick={() => setIncludeMode(false)}
              >
                {t("filters.exclude")}
              </button>
            </div>
            <div className="include-exclude-options">
              {options.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  className={`filter-option${selectedValues.includes(option.value) ? " selected" : ""}`}
                  onClick={() => toggleSelection(option.value)}
                  aria-pressed={selectedValues.includes(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </FilterSection>
  );
}