import { useTranslation } from "react-i18next";
import "./ListingFormSection.css";
import "./BasicDetailsSection.css";
import { LISTING_LIMITS } from "../../../constants/listingLimits";
import { EQUIPMENT_CATEGORIES, EQUIPMENT_CONDITIONS } from "../../../constants/equipment";

const species = ["ballPythons", "crestedGeckos", "leopardGeckos"];

// The category (live animal vs equipment) is chosen by CategorySwitch at the top of the form.
export default function BasicDetailsSection({ formData, onChange, onSpeciesChange }) {
  const { t } = useTranslation();
  const speciesOptions = species.map((speciesKey) => ({
    key: speciesKey,
    label: t(`species.${speciesKey}`),
  }));
  const searchTerm = formData.species.trim().toLocaleLowerCase();
  const matchingSpecies = searchTerm
    ? speciesOptions.filter(({ label }) => label.toLocaleLowerCase().includes(searchTerm))
    : [];

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
            <div className="basic-details-species">
              <input
                id="listing-species"
                type="text"
                value={species.includes(formData.species) ? t(`species.${formData.species}`) : formData.species}
                onChange={(event) => onSpeciesChange(event.target.value)}
                maxLength={LISTING_LIMITS.speciesLength}
                className="listing-form-input listing-form-input--fixed"
                placeholder={t("createListing.basic.speciesPlaceholder")}
                autoComplete="off"
                required
              />
              {searchTerm && (
                <div role="listbox" aria-label={t("createListing.basic.speciesOptions")} className="basic-details-species-menu">
                  {matchingSpecies.length > 0 ? matchingSpecies.map(({ key, label }) => (
                    <button key={key} type="button" role="option" aria-selected={formData.species === key} onClick={() => onSpeciesChange(key)} className="basic-details-species-option">
                      {label}
                    </button>
                  )) : (
                    <button type="button" role="option" onClick={() => onSpeciesChange(formData.species)} className="basic-details-species-option">
                      {t("createListing.basic.other")}
                    </button>
                  )}
                </div>
              )}
            </div>
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
