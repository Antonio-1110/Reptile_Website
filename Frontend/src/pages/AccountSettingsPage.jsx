import "./AccountSettingsPage.css";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getCurrentProfile, updateCurrentProfile } from "../api/listingsApi";
import BackLink from "../components/ui/BackLink";
import EmptyState from "../components/ui/EmptyState";
import { errorText, toErrorState } from "../utils/errorState";
import { Link } from "react-router";

// Form field → the profile API field whose validation errors belong under it.
const FIELD_ERROR_KEYS = {
  username: "username",
  displayName: "first_name",
  phoneNumber: "phone_number",
  lineId: "line_id",
  contactEmail: "contact_email",
  instagram: "instagram",
  facebook: "facebook",
  bio: "bio",
};

function toForm(profile) {
  return {
    username: profile.username || "",
    displayName: profile.display_name || "",
    phoneNumber: profile.phone_number || "",
    lineId: profile.line_id || "",
    contactEmail: profile.contact_email || "",
    instagram: profile.instagram || "",
    facebook: profile.facebook || "",
    bio: profile.bio || "",
  };
}

function AccountSettingsPage() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [savedMessage, setSavedMessage] = useState("");

  const loadProfile = () => {
    setLoadError(null);
    getCurrentProfile()
      .then((loaded) => {
        setProfile(loaded);
        setForm(toForm(loaded));
      })
      .catch((error) => setLoadError(toErrorState(error, "accountSettings.loadError")));
  };

  useEffect(loadProfile, []);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setSavedMessage("");
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setSaving(true);
    setSaveError("");
    setFieldErrors({});
    setSavedMessage("");

    const payload = {
      username: form.username.trim(),
      phone_number: form.phoneNumber.trim(),
      line_id: form.lineId.trim(),
      contact_email: form.contactEmail.trim(),
      instagram: form.instagram.trim(),
      facebook: form.facebook.trim(),
      bio: form.bio.trim(),
    };
    // The backend derives display_name from first/last name. Only rewrite them when the display name
    // was actually edited, so accounts with a separate first and last name keep them.
    const displayName = form.displayName.trim();
    if (displayName !== profile.display_name) {
      payload.first_name = displayName;
      payload.last_name = "";
    }

    try {
      const saved = await updateCurrentProfile(payload);
      setProfile(saved);
      setForm(toForm(saved));
      setSavedMessage(t("accountSettings.saved"));
    } catch (error) {
      const errors = Object.fromEntries(
        Object.entries(FIELD_ERROR_KEYS)
          .filter(([, apiField]) => error.fields?.[apiField])
          .map(([field, apiField]) => [field, error.fields[apiField]]),
      );
      setFieldErrors(errors);
      setSaveError(Object.keys(errors).length ? t("accountSettings.fixErrors") : error.message || t("accountSettings.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const fieldError = (field) =>
    fieldErrors[field] && <span role="alert" className="account-settings-field-error">{fieldErrors[field]}</span>;

  const header = (
    <div className="account-settings-header">
      <BackLink to="/marketplace">{t("navigation.backToMarketplace")}</BackLink>
      <p className="account-settings-kicker">{t("navigation.account")}</p>
      <h1 className="account-settings-title">{t("accountSettings.title")}</h1>
    </div>
  );

  if (!form) {
    return (
      <div className="account-settings-page">
        {header}
        {loadError ? (
          <EmptyState
            tone="error"
            title={errorText(t, loadError)}
            actions={<button type="button" onClick={loadProfile}>{t("listings.retry")}</button>}
          />
        ) : (
          <p className="account-settings-loading" role="status">{t("accountSettings.loading")}</p>
        )}
      </div>
    );
  }

  const isCommercial = profile.account_type === "commercial";

  return (
    <div className="account-settings-page">
      {header}

      <form onSubmit={handleSave} className="account-settings-form">
        <section className="account-settings-section">
          <h2 className="account-settings-section-title">{t("accountSettings.profileDetails")}</h2>

          <div className="account-settings-row">
            <label className="account-settings-field">
              {t("accountSettings.username")}
              <input value={form.username} onChange={(event) => updateField("username", event.target.value)} className="account-settings-input" required maxLength={150} autoComplete="username" />
              {fieldError("username")}
            </label>

            <label className="account-settings-field">
              {t("accountSettings.displayName")}
              <input value={form.displayName} onChange={(event) => updateField("displayName", event.target.value)} className="account-settings-input" maxLength={150} />
              {fieldError("displayName")}
            </label>
          </div>

          <div className="account-settings-row">
            {/* Read-only: commercial is a paid upgrade, handled outside this page. */}
            <div className="account-settings-field">
              {t("accountSettings.accountType")}
              <p className="account-settings-plan">
                {t(`accountSettings.accountTypes.${profile.account_type}`)}
                {profile.is_paid_account && ` · ${t("accountSettings.paidPlan")}`}
              </p>
              <p className="account-settings-plan-limits">
                {t("accountSettings.planLimits", { posts: profile.max_post_count, photos: profile.max_images_per_post })}
              </p>
              {!isCommercial && <Link to="/upgrade" className="account-settings-upgrade-link">{t("accountSettings.upgradeLink")}</Link>}
            </div>

            <label className="account-settings-field">
              {t("accountSettings.email")}
              <input value={profile.email || ""} className="account-settings-input" readOnly disabled />
            </label>
          </div>

          <div className="account-settings-identity">
            <p className="account-settings-identity-label">{t("accountSettings.publicIdentity")}</p>
            <p className="account-settings-identity-tag">{profile.username}</p>
            <p className="account-settings-identity-note">
              {t("accountSettings.identityNote")}
            </p>
          </div>
        </section>

        <section className="account-settings-section">
          <h2 className="account-settings-section-title">{t("accountSettings.communication")}</h2>

          <div className="account-settings-row">
            <label className="account-settings-field">
              {t("accountSettings.phoneNumber")}
              <input value={form.phoneNumber} onChange={(event) => updateField("phoneNumber", event.target.value)} className="account-settings-input" placeholder="0912-345-678" maxLength={15} autoComplete="tel" />
              {fieldError("phoneNumber")}
            </label>

            <label className="account-settings-field">
              {t("accountSettings.lineId")}
              <input value={form.lineId} onChange={(event) => updateField("lineId", event.target.value)} className="account-settings-input" placeholder="lineid" maxLength={40} />
              {fieldError("lineId")}
            </label>
          </div>

          <div className="account-settings-row">
            <label className="account-settings-field">
              {t("accountSettings.contactEmail")}
              <input type="email" value={form.contactEmail} onChange={(event) => updateField("contactEmail", event.target.value)} className="account-settings-input" placeholder="hello@example.com" maxLength={254} autoComplete="email" />
              {fieldError("contactEmail")}
            </label>

            <label className="account-settings-field">
              {t("accountSettings.instagram")}
              <input value={form.instagram} onChange={(event) => updateField("instagram", event.target.value)} className="account-settings-input" placeholder="@yourshop" maxLength={60} />
              {fieldError("instagram")}
            </label>
          </div>

          <div className="account-settings-row">
            <label className="account-settings-field">
              {t("accountSettings.facebook")}
              <input value={form.facebook} onChange={(event) => updateField("facebook", event.target.value)} className="account-settings-input" placeholder={t("accountSettings.facebookPlaceholder")} maxLength={200} />
              {fieldError("facebook")}
            </label>
          </div>
        </section>

        {isCommercial && (
          <section className="account-settings-section">
            <h2 className="account-settings-section-title">{t("accountSettings.commercialProfile")}</h2>

            <label className="account-settings-field">
              {t("accountSettings.businessBio")}
              <textarea value={form.bio} onChange={(event) => updateField("bio", event.target.value)} className="account-settings-input account-settings-textarea" placeholder={t("accountSettings.businessBioPlaceholder")} maxLength={500} />
              {fieldError("bio")}
            </label>
          </section>
        )}

        <div className="account-settings-footer">
          <button type="submit" className="account-settings-save" disabled={saving}>
            {saving ? t("accountSettings.saving") : t("accountSettings.save")}
          </button>
          {saveError && <span role="alert" className="account-settings-error">{saveError}</span>}
          {savedMessage && <span className="account-settings-saved">{savedMessage}</span>}
        </div>
      </form>
    </div>
  );
}

export default AccountSettingsPage;
