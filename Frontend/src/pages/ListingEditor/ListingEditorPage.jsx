import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import "./ListingEditorPage.css";
import BasicDetailsSection from "./components/BasicDetailsSection";
import BiologicalDataSection from "./components/BiologicalDataSection";
import CategorySwitch from "../../components/ui/CategorySwitch";
import LogisticsSection from "./components/LogisticsSection";
import MediaUploader from "./components/MediaUploader";
import { createListing, getCurrentProfile, getRawListing, getSexKey, updateListing, uploadListingPhotos } from "../../api/listingsApi";
import { getLocationKey } from "../../constants/locations";
import { DEFAULT_EQUIPMENT_CATEGORY, DEFAULT_EQUIPMENT_CONDITION } from "../../constants/equipment";
import { errorText, toErrorState } from "../../utils/errorState";

const EDITOR_CATEGORIES = ["live_animal", "enclosure"];

const initialFormData = {
  title: "",
  description: "",
  price: "",
  category: "live_animal",
  species: "",
  sex: "unsexed",
  genetics: "",
  lifeStage: "adult",
  ageYears: "",
  weight: "",
  size: "",
  diets: [],
  equipmentCategory: DEFAULT_EQUIPMENT_CATEGORY,
  condition: String(DEFAULT_EQUIPMENT_CONDITION),
  location: "",
  shippingMethods: [],
  legalAgreed: false,
  media: [],
};

export default function ListingEditorPage({ editId = null, editCategory = null }) {
  const { t } = useTranslation();
  const isEditing = Boolean(editId);
  const [formData, setFormData] = useState(initialFormData);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [quota, setQuota] = useState(null);
  const [quotaLoading, setQuotaLoading] = useState(true);
  const [quotaError, setQuotaError] = useState(null);
  const [coverIndex, setCoverIndex] = useState(0);
  const [listingLoading, setListingLoading] = useState(isEditing);
  const [listingLoadError, setListingLoadError] = useState(null);
  const mediaRef = useRef(formData.media);

  mediaRef.current = formData.media;
  useEffect(() => () => {
    mediaRef.current.forEach(({ previewUrl, originalPreviewUrl }) => {
      URL.revokeObjectURL(previewUrl);
      if (originalPreviewUrl && originalPreviewUrl !== previewUrl) URL.revokeObjectURL(originalPreviewUrl);
    });
  }, []);

  useEffect(() => {
    getCurrentProfile()
      .then(setQuota)
      .catch((error) => setQuotaError(toErrorState(error, "createListing.errors.signInToPublish")))
      .finally(() => setQuotaLoading(false));
  }, []);

  useEffect(() => {
    if (!isEditing) return;
    setListingLoading(true);
    getRawListing(editId, editCategory)
      .then((raw) => {
        setFormData((current) => ({
          ...current,
          title: raw.title || "",
          description: raw.description || "",
          price: raw.price != null ? String(raw.price) : "",
          category: editCategory === "equipment" ? "enclosure" : "live_animal",
          species: raw.species_name || "",
          sex: getSexKey(raw.sex),
          genetics: raw.genetics || "",
          lifeStage: raw.life_stage || "adult",
          ageYears: raw.age_years != null ? String(raw.age_years) : "",
          weight: raw.weight_grams != null ? String(raw.weight_grams) : "",
          size: raw.size_cm != null ? String(raw.size_cm) : "",
          diets: raw.diets || [],
          equipmentCategory: raw.category || DEFAULT_EQUIPMENT_CATEGORY,
          condition: String(raw.condition ?? DEFAULT_EQUIPMENT_CONDITION),
          location: getLocationKey(raw.location),
          shippingMethods: raw.shipping_methods || [],
          legalAgreed: true,
        }));
      })
      .catch((error) => setListingLoadError(toErrorState(error, "createListing.errors.loadForEdit")))
      .finally(() => setListingLoading(false));
  }, [isEditing, editId, editCategory]);

  const updateFormData = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
    setSubmitted(false);
  };

  const updateField = (name, value) => {
    setFormData((current) => ({ ...current, [name]: value }));
    setSubmitted(false);
  };

  const handleCategoryChange = (value) => {
    setFormData((current) => ({
      ...current,
      category: value,
      ...(value !== "live_animal" ? { species: "" } : {}),
    }));
    setSubmitted(false);
  };

  const toggleShippingMethod = (method) => {
    setFormData((current) => ({
      ...current,
      shippingMethods: current.shippingMethods.includes(method)
        ? current.shippingMethods.filter((item) => item !== method)
        : [...current.shippingMethods, method],
    }));
  };

  const toggleDiet = (diet) => {
    setFormData((current) => ({
      ...current,
      diets: current.diets.includes(diet)
        ? current.diets.filter((item) => item !== diet)
        : [...current.diets, diet],
    }));
  };

  // Photos upload after the listing itself is saved; selecting none keeps the listing's current photos.
  const uploadPhotos = async (listingId) => {
    if (!formData.media.length) return true;
    const category = formData.category === "live_animal" ? "live_animal" : "equipment";
    try {
      await uploadListingPhotos(listingId, category, formData.media.map(({ file }) => file), coverIndex);
      return true;
    } catch (error) {
      setSubmitError(t("createListing.errors.photos", { reason: error.message }));
      return false;
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitted(false);
    setSubmitError("");
    if (isEditing) {
      setSubmitting(true);
      try {
        await updateListing(editId, formData);
        if (await uploadPhotos(editId)) setSubmitted(true);
      } catch (error) {
        setSubmitError(error.message || t("createListing.errors.update"));
      } finally {
        setSubmitting(false);
      }
      return;
    }
    if (!quota || quota.remaining_post_count <= 0) {
      setSubmitError(t("createListing.quotaReached"));
      return;
    }
    setSubmitting(true);
    try {
      const created = await createListing(formData);
      setQuota(await getCurrentProfile());
      if (await uploadPhotos(created.id)) setSubmitted(true);
    } catch (error) {
      setSubmitError(error.message || t("createListing.errors.publish"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <main className="listing-editor-page">
        <div className="listing-editor-card">
        <a href={isEditing ? "/my-listings" : "/marketplace"} className="listing-editor-back">
          {isEditing ? t("createListing.edit.back") : t("navigation.backToMarketplace")}
        </a>
        <h1 className="listing-editor-title">{isEditing ? t("createListing.edit.heading") : t("createListing.heading")}</h1>
        <p className="listing-editor-subtitle">{isEditing ? t("createListing.edit.subtitle") : t("createListing.subtitle")}</p>
        {listingLoadError && <p role="alert" className="listing-editor-notice listing-editor-notice--error">{errorText(t, listingLoadError)}</p>}
        {!isEditing && quota && <p className="listing-editor-notice">{t("createListing.quota", { remaining: quota.remaining_post_count, max: quota.max_post_count })}</p>}
        {!isEditing && quotaError && <p role="alert" className="listing-editor-notice listing-editor-notice--error">{errorText(t, quotaError)}</p>}
        {!isEditing && quota && quota.remaining_post_count === 0 && <p role="alert" className="listing-editor-notice listing-editor-notice--error">{t("createListing.quotaReached")}</p>}
        {listingLoading ? (
          <p className="listing-editor-loading">{t("createListing.loading")}</p>
        ) : (
        <form onSubmit={handleSubmit} className="listing-editor-form">
          {/* "enclosure" is the equipment category; the editor maps it to the equipment endpoint. A
              listing can't move between the two endpoints, so the switch is locked when editing. */}
          <CategorySwitch
            className="category-switch-section"
            labelClassName="listing-form-label"
            label={t("createListing.basic.category")}
            options={EDITOR_CATEGORIES.map((value) => ({ value, label: t(`createListing.categories.${value}`) }))}
            value={formData.category}
            onChange={handleCategoryChange}
            disabled={isEditing}
            hint={isEditing && <p className="listing-form-hint">{t("createListing.basic.categoryLocked")}</p>}
          />
          <MediaUploader
            files={formData.media}
            coverIndex={coverIndex}
            maxCount={quota?.max_images_per_post}
            replacesExisting={isEditing}
            onChange={(files) => updateField("media", files)}
            onCoverChange={setCoverIndex}
          />
          <BasicDetailsSection formData={formData} onChange={updateFormData} onSpeciesChange={(species) => updateField("species", species)} />
          {formData.category === "live_animal" && (
            <BiologicalDataSection
              formData={formData}
              onChange={updateFormData}
              onSexChange={(sex) => updateField("sex", sex)}
              onGeneticsChange={(event) => updateField("genetics", event.target.value)}
              onDietChange={toggleDiet}
            />
          )}
          <LogisticsSection formData={formData} onChange={updateFormData} onShippingChange={toggleShippingMethod} />
          <button type="submit" disabled={!formData.legalAgreed || submitting || (!isEditing && (quotaLoading || !quota || quota.remaining_post_count === 0))} className="listing-editor-submit">
            {isEditing ? (submitting ? t("createListing.edit.saving") : t("createListing.edit.save")) : t("createListing.submit")}
          </button>
          {submitError && <p role="alert" className="listing-editor-result listing-editor-result--error">{submitError}</p>}
          {submitted && <p className="listing-editor-result listing-editor-result--success">{isEditing ? t("createListing.edit.success") : t("createListing.success")}</p>}
        </form>
        )}
        </div>
      </main>
    </>
  );
}
