import { useEffect } from "react";
import { useTranslation } from "react-i18next";

const DESCRIPTION_LENGTH = 160; // about what Google shows under a result

// The description in index.html, which covers every page that doesn't set its own.
const defaultDescription = () => document.querySelector('meta[name="description"]')?.dataset.default;

function setDescription(content) {
  const meta = document.querySelector('meta[name="description"]');
  if (!meta) return;
  if (meta.dataset.default === undefined) meta.dataset.default = meta.content;
  meta.content = content;
}

export function shortDescription(text) {
  const flat = (text || "").replace(/\s+/g, " ").trim();
  return flat.length > DESCRIPTION_LENGTH ? `${flat.slice(0, DESCRIPTION_LENGTH - 1).trimEnd()}…` : flat;
}

// Gives a page its own tab title and search-result snippet. Google runs the app's JavaScript before
// indexing, so this is what it lists the page under; without it every page is just "Reptilian".
// Pass nothing (e.g. while loading) to keep the site-wide ones.
export default function usePageMeta(title, description) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;

  useEffect(() => {
    if (!title) return undefined;
    document.title = t("app.pageTitle", { page: title });
    if (description) setDescription(shortDescription(description));
    return () => {
      document.title = t("app.title");
      const original = defaultDescription();
      if (original !== undefined) setDescription(original);
    };
    // `language` re-applies the title after a language switch resets it (see i18n/index.js).
  }, [title, description, language, t]);
}
