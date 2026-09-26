import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import "./ListingFormSection.css";
import "./BasicDetailsSection.css";
import { LISTING_LIMITS } from "../../../constants/listingLimits";
import { EQUIPMENT_CATEGORIES, EQUIPMENT_CONDITIONS } from "../../../constants/equipment";
import { getSpeciesLabel, matchSpecies } from "../../../constants/species";

// The category (live animal vs equipment) is chosen by CategorySwitch at the top of the form.
// `speciesList` is null until the species list loads (or if it can't): typing still works, the server
// matches the name itself.
export default function BasicDetailsSection({ formData, onChange, onSpeciesChange, speciesList }) {
  const { t } = useTranslation();
  const [speciesMenuOpen, setSpeciesMenuOpen] = useState(false);
  // The option the arrow keys have highlighted (-1: none); focus stays in the input throughout.
  const [activeOption, setActiveOption] = useState(-1);
  const selectedSpecies = speciesList?.find((species) => species.id === formData.speciesId);
  const typedSpecies = formData.species.trim();
  const { matches: matchingSpecies, exact: exactSpecies } = formData.speciesId
    ? { matches: [], exact: null }
    : matchSpecies(t, speciesList || [], typedSpecies);
  // A name that isn't in the list can still be posted, but the listing waits for a species review.
  const needsReview = Boolean(speciesList && typedSpecies && !formData.speciesId && !exactSpecies);

  const closeSpeciesMenu = () => {
    setSpeciesMenuOpen(false);
    setActiveOption(-1);
  };
  // What the menu offers, in order: matching species, then (unless one matches exactly) the typed name.
  const speciesOptions = [
    ...matchingSpecies.map((species) => ({
      key: species.id,
      label: getSpeciesLabel(t, species.name),
      choose: () => onSpeciesChange(species.name, species.id),
    })),
    ...(exactSpecies ? [] : [{ key: "review", label: t("speciesReview.useTyped", { name: typedSpecies }), review: true, choose: () => {} }]),
  ];
  const speciesMenuVisible = speciesMenuOpen && Boolean(typedSpecies) && !formData.speciesId;
  const activeOptionId = speciesMenuVisible && activeOption >= 0 && activeOption < speciesOptions.length
    ? `listing-species-option-${activeOption}`
    : undefined;

  useEffect(() => {
    if (activeOptionId) document.getElementById(activeOptionId)?.scrollIntoView?.({ block: "nearest" });
  }, [activeOptionId]);

  const chooseSpeciesOption = (option) => {
    option.choose();
    closeSpeciesMenu();
  };

  const handleSpeciesKeyDown = (event) => {
    const count = speciesOptions.length;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!typedSpecies || formData.speciesId || !count) return;
      event.preventDefault(); // keep the caret where it is
      const step = event.key === "ArrowDown" ? 1 : -1;
      setSpeciesMenuOpen(true);
      // Wraps around at either end; the first press starts from the top (Down) or bottom (Up).
      setActiveOption((current) => (!speciesMenuVisible || current < 0 ? (step > 0 ? 0 : count - 1) : (current + step + count) % count));
    } else if (event.key === "Enter" && activeOptionId) {
      event.preventDefault(); // pick the option instead of submitting the form
      chooseSpeciesOption(speciesOptions[activeOption]);
    } else if (event.key === "Escape" && speciesMenuVisible) {
      event.preventDefault();
      closeSpeciesMenu();
    }
  };

  return (
    <section className="listing-form-section">
      <h2 className="listing-form-section-title">{t("createListing.basic.title")}</h2>
      <div>
        <label htmlFor="listing-title" className="listing-form-label">{t("createListing.basic.titleLabel")}</label>
        <input id="listing-title" type="text" name="title" value={formData.title} onChange={onChange} maxLength={LISTING_LIMITS.titleLength} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.basic.titlePlaceholder")} required />
      </div>
      <div>
        <label htmlFor="listing-description" className="listing-form-label">{t("createListing.basic.description")}</label>
        <textarea id="listing-description" name="description" value={formData.description} onChange={onChange} maxLength={LISTING_LIMITS.descriptionLength} className="listing-form-input listing-form-input--fixed basic-details-description" placeholder={t("createListing.basic.descriptionPlaceholder")} required />
      </div>
      <div className="listing-form-grid listing-form-grid--2">
        <div>
          <label htmlFor="listing-price" className="listing-form-label">{t("createListing.basic.price")}</label>
          <input id="listing-price" type="number" name="price" min="0" max={LISTING_LIMITS.price} value={formData.price} onChange={onChange} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.basic.pricePlaceholder")} required />
        </div>
        {formData.category === "live_animal" && (
          <div>
            <label htmlFor="listing-species" className="listing-form-label">{t("createListing.basic.species")}</label>
            <div
              className="basic-details-species"
              onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) closeSpeciesMenu(); }}
            >
              <input
                id="listing-species"
                type="text"
                value={selectedSpecies ? getSpeciesLabel(t, selectedSpecies.name) : formData.species}
                onChange={(event) => {
                  onSpeciesChange(event.target.value, null);
                  setSpeciesMenuOpen(true);
                  setActiveOption(-1);
                }}
                onKeyDown={handleSpeciesKeyDown}
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={speciesMenuVisible}
                aria-controls="listing-species-options"
                aria-activedescendant={activeOptionId}
                maxLength={LISTING_LIMITS.speciesLength}
                className="listing-form-input listing-form-input--fixed"
                placeholder={t("createListing.basic.speciesPlaceholder")}
                autoComplete="off"
                aria-describedby={needsReview ? "listing-species-review" : undefined}
                required
              />
              {speciesMenuVisible && (
                // preventDefault keeps focus in the input, so picking an option doesn't close the menu first.
                <div id="listing-species-options" role="listbox" aria-label={t("createListing.basic.speciesOptions")} className="basic-details-species-menu" onMouseDown={(event) => event.preventDefault()}>
                  {speciesOptions.map((option, index) => (
                    // tabIndex -1: the arrow keys move through the options, so Tab goes on to the next field.
                    <button
                      key={option.key}
                      id={`listing-species-option-${index}`}
                      type="button"
                      role="option"
                      tabIndex={-1}
                      aria-selected={index === activeOption}
                      onClick={() => chooseSpeciesOption(option)}
                      onMouseEnter={() => setActiveOption(index)}
                      className={`basic-details-species-option${option.review ? " basic-details-species-option--review" : ""}${index === activeOption ? " is-active" : ""}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {needsReview && (
              <p id="listing-species-review" className="listing-form-hint basic-details-species-review">
                {t("speciesReview.notListed", { name: typedSpecies })}
              </p>
            )}
          </div>
        )}
      </div>
      {formData.category !== "live_animal" && (
        <div className="listing-form-grid listing-form-grid--2">
          <div>
            <label htmlFor="listing-equipment-type" className="listing-form-label">{t("createListing.equipment.type")}</label>
            <select id="listing-equipment-type" name="equipmentCategory" value={formData.equipmentCategory} onChange={onChange} className="listing-form-input listing-form-input--fixed">
              {EQUIPMENT_CATEGORIES.map((key) => <option key={key} value={key}>{t(`createListing.equipment.types.${key}`)}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="listing-condition" className="listing-form-label">{t("createListing.equipment.condition")}</label>
            <select id="listing-condition" name="condition" value={formData.condition} onChange={onChange} className="listing-form-input listing-form-input--fixed">
              {EQUIPMENT_CONDITIONS.map((code) => <option key={code} value={String(code)}>{t(`createListing.equipment.conditions.${code}`)}</option>)}
            </select>
          </div>
        </div>
      )}
    </section>
  );
}
