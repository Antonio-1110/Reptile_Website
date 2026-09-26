import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import { en, zh } from "./locales";

const resources = {
  en: { translation: en },
  zh: { translation: zh },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: ["en", "zh"],
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
    interpolation: {
      escapeValue: false,
    },
  });

// Keep <html lang> (screen readers, fonts, hyphenation) and the tab title in the UI language.
const syncDocument = (language) => {
  document.documentElement.lang = language === "zh" ? "zh-Hant" : "en";
  document.title = i18n.t("app.title");
};
syncDocument(i18n.resolvedLanguage);
i18n.on("languageChanged", () => syncDocument(i18n.resolvedLanguage));

export default i18n;
