import { useCallback, useId, useRef, useState } from "react";
import Cropper from "react-easy-crop";
import { useTranslation } from "react-i18next";
import useDialogFocus from "../../hooks/useDialogFocus";
import { getCroppedImg } from "../../utils/cropImage";
import "./ImageCropModal.css";

export const COVER_ASPECT_RATIO = 4 / 3;

const MIN_ZOOM = 1;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.1;

export default function ImageCropModal({ imageSrc, fileName, aspect = COVER_ASPECT_RATIO, onCancel, onSave }) {
  const { t } = useTranslation();
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dialogRef = useRef(null);
  const zoomRef = useRef(null);
  const titleId = useId();
  const hintId = useId();
  // Escape cancels (not while saving); focus starts on the zoom slider, and Tab stays in the dialog.
  useDialogFocus(dialogRef, () => !saving && onCancel(), zoomRef);

  // + / − zoom from anywhere in the dialog, so the crop can be set without a mouse (the arrow keys
  // already move the photo when the crop area has focus).
  const handleKeyDown = (event) => {
    if (event.target.id === "crop-zoom") return; // the slider handles its own keys
    const change = { "+": ZOOM_STEP, "=": ZOOM_STEP, "-": -ZOOM_STEP, _: -ZOOM_STEP }[event.key];
    if (change === undefined) return;
    event.preventDefault();
    setZoom((current) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current + change)));
  };

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
    <div className="crop-modal-overlay">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={hintId}
        tabIndex={-1}
        className="crop-modal"
        onKeyDown={handleKeyDown}
      >
        <div className="crop-modal-header">
          <h2 id={titleId} className="crop-modal-title">{t("createListing.media.crop.title")}</h2>
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
            minZoom={MIN_ZOOM}
            maxZoom={MAX_ZOOM}
            cropperProps={{ "aria-label": t("createListing.media.crop.area"), "aria-describedby": hintId, role: "group" }}
          />
        </div>
        <p id={hintId} className="crop-modal-hint">{t("createListing.media.crop.keyboardHint")}</p>

        <div>
          <label htmlFor="crop-zoom" className="crop-modal-zoom-label">
            {t("createListing.media.crop.zoom")}
          </label>
          <input
            ref={zoomRef}
            id="crop-zoom"
            type="range"
            min={MIN_ZOOM}
            max={MAX_ZOOM}
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
