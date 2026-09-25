import { useId, useRef } from "react";
import "./CategorySwitch.css";

// iOS-style segmented control: a pill slides under the chosen option. It's a radio group, so arrow keys
// move the choice and only the selected option is in the tab order. Used by the listing editor (what
// you're posting) and the marketplace filters (what you're browsing).
// options: [{ value, label }]; labelClassName styles the visible label to match the surrounding form.
export default function CategorySwitch({
  options, value, onChange, label, labelClassName, hint, disabled = false, className = "",
}) {
  const labelId = useId();
  const optionRefs = useRef([]);
  const selectedIndex = Math.max(options.findIndex((option) => option.value === value), 0);

  const select = (index) => {
    if (disabled) return;
    onChange(options[index].value);
    optionRefs.current[index]?.focus();
  };

  const handleKeyDown = (event) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    select((selectedIndex + step + options.length) % options.length);
  };

  return (
    <section className={className}>
      <p id={labelId} className={labelClassName}>{label}</p>
      <div
        role="radiogroup"
        aria-labelledby={labelId}
        aria-disabled={disabled || undefined}
        className={`category-switch${disabled ? " is-disabled" : ""}`}
        style={{ "--category-count": options.length, "--category-index": selectedIndex }}
        onKeyDown={handleKeyDown}
      >
        <span className="category-switch-thumb" aria-hidden="true" />
        {options.map((option, index) => (
          <button
            key={option.value}
            ref={(element) => { optionRefs.current[index] = element; }}
            type="button"
            role="radio"
            aria-checked={index === selectedIndex}
            tabIndex={index === selectedIndex ? 0 : -1}
            disabled={disabled && index !== selectedIndex}
            onClick={() => select(index)}
            className={`category-switch-option${index === selectedIndex ? " is-selected" : ""}`}
          >
            {option.label}
          </button>
        ))}
      </div>
      {hint}
    </section>
  );
}
