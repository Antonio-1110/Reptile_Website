import { useTranslation } from "react-i18next";
import "./ListingFormSection.css";
import "./BiologicalDataSection.css";
import { LISTING_LIMITS } from "../../../constants/listingLimits";

const sexOptions = ["male", "female", "unsexed"];
const lifeStages = ["hatchling", "juvenile", "subAdult", "adult"];
const diets = ["live", "frozenThawed", "pellets"];

export default function BiologicalDataSection({ formData, onChange, onSexChange, onGeneticsChange, onDietChange }) {
  const { t } = useTranslation();
  const handleGeneticsChange = (event) => {
    const traits = event.target.value.split("/");
    const hasLongTrait = traits.some((trait) => trait.trim().split(/\s+/).filter(Boolean).length > LISTING_LIMITS.geneticsWordsPerTrait);
    if (traits.length <= LISTING_LIMITS.geneticsTraits && !hasLongTrait) onGeneticsChange(event);
  };

  return (
    <section className="listing-form-section listing-form-section--divided">
      <h2 className="listing-form-section-title">{t("createListing.biological.title")}</h2>
      <fieldset>
        <legend className="listing-form-label">{t("createListing.biological.sex")}</legend>
        <div className="biological-sex-options">
          {sexOptions.map((sex) => (
            <button key={sex} type="button" onClick={() => onSexChange(sex)} className={`biological-sex-option${formData.sex === sex ? " is-selected" : ""}`}>
              {t(`createListing.sex.${sex}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <div>
        <label htmlFor="listing-genetics" className="listing-form-label">{t("createListing.biological.genetics")}</label>
        <input id="listing-genetics" type="text" value={formData.genetics} onChange={handleGeneticsChange} maxLength={LISTING_LIMITS.geneticsLength} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.biological.geneticsPlaceholder")} />
        <div className="biological-traits">
          {formData.genetics.split("/").map((trait) => trait.trim()).filter(Boolean).map((trait) => <span key={trait} className="biological-trait">{trait}</span>)}
        </div>
      </div>
      <div className="listing-form-grid listing-form-grid--4">
        <div>
          <label htmlFor="listing-life-stage" className="listing-form-label">{t("createListing.biological.lifeStage")}</label>
          <select id="listing-life-stage" name="lifeStage" value={formData.lifeStage} onChange={onChange} className="listing-form-input listing-form-input--fixed">{lifeStages.map((stage) => <option key={stage} value={stage}>{t(`createListing.lifeStages.${stage}`)}</option>)}</select>
        </div>
        <div>
          <label htmlFor="listing-age-years" className="listing-form-label">{t("createListing.biological.ageYears")}</label>
          <input id="listing-age-years" type="number" name="ageYears" min="0" max={LISTING_LIMITS.ageYears} step="0.1" value={formData.ageYears} onChange={onChange} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.biological.ageYearsPlaceholder")} />
        </div>
        <div>
          <label htmlFor="listing-weight" className="listing-form-label">{t("createListing.biological.weight")}</label>
          <input id="listing-weight" type="number" name="weight" min="0" max={LISTING_LIMITS.weightGrams} step="0.1" value={formData.weight} onChange={onChange} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.biological.weightPlaceholder")} />
        </div>
        <div>
          <label htmlFor="listing-size" className="listing-form-label">{t("createListing.biological.size")}</label>
          <input id="listing-size" type="number" name="size" min="0" max={LISTING_LIMITS.sizeCm} step="0.1" value={formData.size} onChange={onChange} className="listing-form-input listing-form-input--fixed" placeholder={t("createListing.biological.sizePlaceholder")} />
        </div>
      </div>
      <fieldset>
        <legend className="listing-form-label">{t("createListing.biological.diet")}</legend>
        <div className="listing-form-choices">
          {diets.map((diet) => (
            <label key={diet} className="listing-form-check-card">
              <input type="checkbox" checked={formData.diets.includes(diet)} onChange={() => onDietChange(diet)} className="listing-form-checkbox" />
              {t(`createListing.diets.${diet}`)}
            </label>
          ))}
        </div>
      </fieldset>
    </section>
  );
}
