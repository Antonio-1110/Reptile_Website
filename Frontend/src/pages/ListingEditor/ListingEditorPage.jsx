import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import "./ListingEditorPage.css";
import BasicDetailsSection from "./components/BasicDetailsSection";
import BiologicalDataSection from "./components/BiologicalDataSection";
import CategorySwitch from "../../components/ui/CategorySwitch";
import LogisticsSection from "./components/LogisticsSection";
import MediaUploader from "./components/MediaUploader";
import { createListing, getCurrentProfile, getRawListing, getSexKey, listingPagePath, saveListingPhotos, updateListing } from "../../api/listingsApi";
import { getLocationKey } from "../../constants/locations";
import { DEFAULT_EQUIPMENT_CATEGORY, DEFAULT_EQUIPMENT_CONDITION } from "../../constants/equipment";
import { errorText, toErrorState } from "../../utils/errorState";
import { existingPhoto, isBlobUrl } from "./mediaItems";

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

// API field → the form label it belongs to, so a server validation error says which field to fix.
const FIELD_LABEL_KEYS = {
  title: "createListing.basic.titleLabel",
  description: "createListing.basic.description",
  price: "createListing.basic.price",
  species: "createListing.basic.species",
  sex: "createListing.biological.sex",
  genetics: "createListing.biological.genetics",
  life_stage: "createListing.biological.lifeStage",
  age_years: "createListing.biological.ageYears",
  weight_grams: "createListing.biological.weight",
  size_cm: "createListing.biological.size",
  diets: "createListing.biological.diet",
  location: "createListing.logistics.location",
  shipping_methods: "createListing.logistics.shipping",
};

function editPath(id, category) {
  return `/postinput?edit=${id}&category=${category}`;
}

// Kept photos preview from their real URL; only local blob previews need revoking.
function revokePreviews(media) {
  media.forEach(({ previewUrl, originalPreviewUrl }) => {
    if (isBlobUrl(previewUrl)) URL.revokeObjectURL(previewUrl);
    if (isBlobUrl(originalPreviewUrl) && originalPreviewUrl !== previewUrl) URL.revokeObjectURL(originalPreviewUrl);
  });
}

export default function ListingEditorPage({ editId = null, editCategory = null }) {
  const { t } = useTranslation();
  const isEditing = Boolean(editId);
  const [formData, setFormData] = useState(initialFormData);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState([]);
  // Set once a new listing is saved; the form is swapped for a summary so it can't be posted twice.
  const [created, setCreated] = useState(null);
  const [quota, setQuota] = useState(null);
  const [quotaLoading, setQuotaLoading] = useState(true);
  const [quotaError, setQuotaError] = useState(null);
  const [coverIndex, setCoverIndex] = useState(0);
  const [listingLoading, setListingLoading] = useState(isEditing);
  const [listingLoadError, setListingLoadError] = useState(null);
  const mediaRef = useRef(formData.media);
  // The listing's photos as loaded (cover first), to skip saving photos when nothing changed.
  const savedPhotosRef = useRef([]);

  mediaRef.current = formData.media;
  useEffect(() => () => revokePreviews(mediaRef.current), []);

  useEffect(() => {
    getCurrentProfile()
      .then(setQuota)
      .catch((error) => setQuotaError(toErrorState(error, "createListing.errors.signInToPublish")))
      .finally(() => setQuotaLoading(false));
  }, []);

  // After saving, the photos just uploaded are the listing's own photos; reloading them means saving
  // again doesn't upload them a second time.
  const reloadSavedPhotos = async (listingId) => {
    const raw = await getRawListing(listingId, editCategory);
    const photos = raw.gallery?.length ? raw.gallery : [raw.image].filter(Boolean);
    savedPhotosRef.current = photos;
    revokePreviews(mediaRef.current);
    setCoverIndex(0);
    setFormData((current) => ({ ...current, media: photos.map(existingPhoto) }));
  };

  useEffect(() => {
    if (!isEditing) return;
    setListingLoading(true);
    getRawListing(editId, editCategory)
      .then((raw) => {
        const photos = raw.gallery?.length ? raw.gallery : [raw.image].filter(Boolean);
        savedPhotosRef.current = photos;
        setCoverIndex(0);
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
          media: photos.map(existingPhoto),
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

  // One line per problem; field errors name the field so the seller knows where to look.
  const describeError = (error, fallbackKey) => {
    const fields = Object.entries(error.fields || {});
    if (!fields.length) return [error.message || t(fallbackKey)];
    return fields.map(([field, message]) => (FIELD_LABEL_KEYS[field]
      ? t("createListing.errors.field", { field: t(FIELD_LABEL_KEYS[field]), message })
      : message));
  };

  // Photos are saved after the listing itself: kept photos by URL, new ones uploaded, cover first.
  // Returns the upload error message, or null when the photos were saved (or didn't change).
  const uploadPhotos = async (listingId) => {
    const { media } = formData;
    const ordered = media.length ? [media[coverIndex], ...media.filter((_, index) => index !== coverIndex)] : [];
    const items = ordered.map((item) => (item.existingUrl ? { url: item.existingUrl } : { file: item.file }));
    const unchanged = items.length === savedPhotosRef.current.length
      && items.every((item, index) => item.url === savedPhotosRef.current[index]);
    if (unchanged) return null;
    const category = formData.category === "live_animal" ? "live_animal" : "equipment";
    try {
      await saveListingPhotos(listingId, category, items);
      return null;
    } catch (error) {
      return error.message;
    }
  };

  const startAnotherListing = () => {
    revokePreviews(formData.media);
    setFormData({ ...initialFormData, category: formData.category });
    setCoverIndex(0);
    setCreated(null);
    setSubmitted(false);
    window.scrollTo(0, 0);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitted(false);
    setSubmitError([]);
    if (isEditing) {
      setSubmitting(true);
      try {
        await updateListing(editId, formData);
        const photoError = await uploadPhotos(editId);
        if (photoError) {
          setSubmitError([t("createListing.errors.photosOnEdit", { reason: photoError })]);
        } else {
          await reloadSavedPhotos(editId);
          setSubmitted(true);
        }
      } catch (error) {
        setSubmitError(describeError(error, "createListing.errors.update"));
      } finally {
        setSubmitting(false);
      }
      return;
    }
    if (!quota || quota.remaining_post_count <= 0) {
      setSubmitError([t("createListing.quotaReached")]);
      return;
    }
    setSubmitting(true);
    try {
      const listing = await createListing(formData);
      const photoError = await uploadPhotos(listing.id);
      // The API's category ("equipment"), not the form's "enclosure", so the links below reach the right page.
      const category = formData.category === "live_animal" ? "live_animal" : "equipment";
      setCreated({ id: listing.id, category, title: listing.title, photoError });
      window.scrollTo(0, 0);
      // The quota only feeds the notice for the next listing; failing to refresh it isn't worth an error.
      getCurrentProfile().then(setQuota).catch(() => {});
    } catch (error) {
      setSubmitError(describeError(error, "createListing.errors.publish"));
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
        {created ? (
          <section className="listing-editor-created" role="status">
            <h2>{t("createListing.created.heading")}</h2>
            <p>{t("createListing.created.body", { title: created.title })}</p>
            {created.photoError && (
              <p className="listing-editor-result--error">
                {t("createListing.errors.photos", { reason: created.photoError })}{" "}
                <a href={editPath(created.id, created.category)}>{t("createListing.created.addPhotos")}</a>
              </p>
            )}
            <div className="listing-editor-created-actions">
              <a href={listingPagePath(created.id, created.category)} className="listing-editor-created-primary">{t("createListing.created.view")}</a>
              <a href="/my-listings">{t("createListing.created.myListings")}</a>
              <button type="button" onClick={startAnotherListing}>{t("createListing.created.another")}</button>
            </div>
          </section>
        ) : listingLoading ? (
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
          <button
            type="submit"
            disabled={!formData.legalAgreed || submitting || (!isEditing && (quotaLoading || !quota || quota.remaining_post_count === 0))}
            aria-describedby={!formData.legalAgreed ? "listing-editor-submit-hint" : undefined}
            className="listing-editor-submit"
          >
            {isEditing
              ? (submitting ? t("createListing.edit.saving") : t("createListing.edit.save"))
              : (submitting ? t("createListing.submitting") : t("createListing.submit"))}
          </button>
          {!formData.legalAgreed && (
            <p id="listing-editor-submit-hint" className="listing-editor-result listing-editor-hint">{t("createListing.complianceHint")}</p>
          )}
          {submitError.length > 0 && (
            <div role="alert" className="listing-editor-result listing-editor-result--error">
              {submitError.map((line) => <p key={line}>{line}</p>)}
            </div>
          )}
          <div role="status">
            {submitted && (
              <p className="listing-editor-result listing-editor-result--success">
                {t("createListing.edit.success")}{" "}
                <a href={listingPagePath(editId, formData.category === "live_animal" ? "live_animal" : "equipment")}>{t("createListing.created.view")}</a>
              </p>
            )}
          </div>
        </form>
        )}
        </div>
      </main>
    </>
  );
}
