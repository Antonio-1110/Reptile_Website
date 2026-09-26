import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

// useTranslation() for text about the listing itself ("the animal is yours"). On equipment pages every
// key is looked up with i18next's `equipment` context first (e.g. `paidToast_equipment`), falling back
// to the plain key, so only the sentences that mention an animal need an equipment variant.
export default function useListingTranslation(category) {
  const translation = useTranslation();
  const { t } = translation;
  const listingT = useCallback(
    (key, options) => (category === 'equipment' ? t(key, { context: 'equipment', ...options }) : t(key, options)),
    [t, category],
  );
  return { ...translation, t: listingT };
}
