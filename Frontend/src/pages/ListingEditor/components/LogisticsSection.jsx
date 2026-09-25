import { useTranslation } from "react-i18next";
import { LOCATION_KEYS } from "../../../constants/locations";
import "./ListingFormSection.css";
import "./LogisticsSection.css";

const shippingMethods = ["localPickup", "shipping"];

export default function LogisticsSection({ formData, onChange, onShippingChange }) {
  const { t } = useTranslation();

  return (
    <section className="listing-form-section listing-form-section--divided">
      <h2 className="listing-form-section-title">{t("createListing.logistics.title")}</h2>
      <div>
        <label htmlFor="listing-location" className="listing-form-label">{t("createListing.logistics.location")}</label>
        <select id="listing-location" name="location" value={formData.location} onChange={onChange} className="listing-form-input" required>
          <option value="">{t("createListing.logistics.locationPlaceholder")}</option>
          {LOCATION_KEYS.map((location) => <option key={location} value={location}>{t(`locations.${location}`)}</option>)}
        </select>
      </div>
      <fieldset>
        <legend className="listing-form-label">{t("createListing.logistics.shipping")}</legend>
        <div className="listing-form-choices">
          {shippingMethods.map((method) => (
            <label key={method} className="listing-form-check-card">
              <input type="checkbox" checked={formData.shippingMethods.includes(method)} onChange={() => onShippingChange(method)} className="listing-form-checkbox" />
              {t(`createListing.shipping.${method}`)}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="logistics-compliance">
        <input type="checkbox" name="legalAgreed" checked={formData.legalAgreed} onChange={onChange} className="logistics-compliance-checkbox" required />
        <span>{t("createListing.logistics.compliance")}</span>
      </label>
    </section>
  );
}
