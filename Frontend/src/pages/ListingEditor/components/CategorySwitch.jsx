import { useRef } from "react";
import { useTranslation } from "react-i18next";
import "./ListingFormSection.css";
import "./CategorySwitch.css";

// Form values; "enclosure" is the equipment category (the editor maps it to the equipment endpoint).
const CATEGORIES = ["live_animal", "enclosure"];

// iOS-style segmented control: a pill slides under the chosen option. It's a radio group, so arrow keys
// move the choice and only the selected option is in the tab order. Disabled when editing, because a
// listing can't change between the live-animal and equipment endpoints after it's created.
export default function CategorySwitch({ value, onChange, disabled = false }) {
  const { t } = useTranslation();
  const optionRefs = useRef([]);
  const selectedIndex = Math.max(CATEGORIES.indexOf(value), 0);

  const select = (index) => {
    if (disabled) return;
    onChange(CATEGORIES[index]);
    optionRefs.current[index]?.focus();
  };

  const handleKeyDown = (event) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    select((selectedIndex + step + CATEGORIES.length) % CATEGORIES.length);
  };

  return (
    <section className="category-switch-section">
      <p id="category-switch-label" className="listing-form-label">{t("createListing.basic.category")}</p>
      <div
        role="radiogroup"
        aria-labelledby="category-switch-label"
        aria-disabled={disabled || undefined}
        className={`category-switch${disabled ? " is-disabled" : ""}`}
        style={{ "--category-count": CATEGORIES.length, "--category-index": selectedIndex }}
        onKeyDown={handleKeyDown}
      >
        <span className="category-switch-thumb" aria-hidden="true" />
        {CATEGORIES.map((category, index) => (
          <button
            key={category}
            ref={(element) => { optionRefs.current[index] = element; }}
            type="button"
            role="radio"
            aria-checked={index === selectedIndex}
            tabIndex={index === selectedIndex ? 0 : -1}
            disabled={disabled && index !== selectedIndex}
            onClick={() => select(index)}
            className={`category-switch-option${index === selectedIndex ? " is-selected" : ""}`}
          >
            {t(`createListing.categories.${category}`)}
          </button>
        ))}
      </div>
      {disabled && <p className="listing-form-hint">{t("createListing.basic.categoryLocked")}</p>}
    </section>
  );
}
