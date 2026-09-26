import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import useDialogFocus from '../../../hooks/useDialogFocus';

// A listing photo at full size. Clicking the backdrop, the × or pressing Escape closes it; focus goes
// to the × while open and back to the photo that opened it afterwards.
export default function ImageLightbox({ src, alt, onClose }) {
  const { t } = useTranslation();
  const dialogRef = useRef(null);
  useDialogFocus(dialogRef, onClose);

  return (
    <div className="listing-detail-lightbox" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={alt}
        className="listing-detail-lightbox-frame"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="listing-detail-lightbox-close" onClick={onClose} aria-label={t('common.dismiss')}>
          ×
        </button>
        <img className="listing-detail-lightbox-image" src={src} alt={alt} />
      </div>
    </div>
  );
}
