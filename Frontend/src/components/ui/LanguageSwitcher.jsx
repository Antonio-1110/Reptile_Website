import { useTranslation } from "react-i18next";
import "./LanguageSwitcher.css";

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const currentLanguage = i18n.resolvedLanguage === "zh" ? "zh" : "en";

  return (
    <div className="language-switcher" aria-label={t("language.label")}>
      <button
        type="button"
        onClick={() => i18n.changeLanguage("en")}
        className={`language-option${currentLanguage === "en" ? " is-active" : ""}`}
        aria-pressed={currentLanguage === "en"}
      >
        {t("language.english")}
      </button>
      <span className="language-divider" aria-hidden="true">/</span>
      <button
        type="button"
        onClick={() => i18n.changeLanguage("zh")}
        className={`language-option${currentLanguage === "zh" ? " is-active" : ""}`}
        aria-pressed={currentLanguage === "zh"}
      >
        {t("language.traditionalChinese")}
      </button>
    </div>
  );
}