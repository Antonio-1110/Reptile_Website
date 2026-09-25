import { useCallback, useState } from "react";
import Cropper from "react-easy-crop";
import { useTranslation } from "react-i18next";
import { getCroppedImg } from "../../utils/cropImage";
import "./ImageCropModal.css";

export const COVER_ASPECT_RATIO = 4 / 3;

export default function ImageCropModal({ imageSrc, fileName, aspect = COVER_ASPECT_RATIO, onCancel, onSave }) {
  const { t } = useTranslation();
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleCropComplete = useCallback((_croppedArea, pixels) => {
    setCroppedAreaPixels(pixels);
  }, []);

  const handleSave = async () => {
    if (!croppedAreaPixels) return;
    setSaving(true);
    setError("");
    try {
      const croppedFile = await getCroppedImg(imageSrc, croppedAreaPixels, fileName);
      onSave(croppedFile);
    } catch (cropError) {
      console.error(cropError);
      setError(t("createListing.media.crop.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("createListing.media.crop.title")}
      className="crop-modal-overlay"
    >
      <div className="crop-modal">
        <div className="crop-modal-header">
          <h2 className="crop-modal-title">{t("createListing.media.crop.title")}</h2>
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            aria-label={t("createListing.media.crop.cancel")}
            className="crop-modal-close"
          >
            ×
          </button>
        </div>

        <div className="crop-modal-canvas">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={handleCropComplete}
          />
        </div>

        <div>
          <label htmlFor="crop-zoom" className="crop-modal-zoom-label">
            {t("createListing.media.crop.zoom")}
          </label>
          <input
            id="crop-zoom"
            type="range"
            min={1}
            max={3}
            step={0.05}
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
            className="crop-modal-zoom-slider"
          />
        </div>

        {error && (
          <p role="alert" className="crop-modal-error">
            {error}
          </p>
        )}

        <div className="crop-modal-actions">
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="crop-modal-button crop-modal-cancel"
          >
            {t("createListing.media.crop.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !croppedAreaPixels}
            className="crop-modal-button crop-modal-save"
          >
            {saving ? t("createListing.media.crop.saving") : t("createListing.media.crop.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
