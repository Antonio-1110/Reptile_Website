import { useState } from "react";
import { useTranslation } from "react-i18next";
import "./ListingFormSection.css";
import "./MediaUploader.css";
import ImageCropModal, { COVER_ASPECT_RATIO } from "../../../components/ui/ImageCropModal";

export const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
export const MAX_IMAGE_COUNT = 3;

// maxCount comes from the account's plan (hobbyist 3, commercial 6, paid 12); the backend enforces it too.
export default function MediaUploader({ files, coverIndex, maxCount = MAX_IMAGE_COUNT, replacesExisting = false, onChange, onCoverChange }) {
  const { t } = useTranslation();
  const [error, setError] = useState("");
  const [cropRequest, setCropRequest] = useState(null); // { index, imageSrc, fileName }
  const hasReachedLimit = files.length >= maxCount;

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    const availableSlots = maxCount - files.length;
    const validFiles = selectedFiles.filter((file) => file.type.startsWith("image/") && file.size <= MAX_IMAGE_SIZE_BYTES);

    if (selectedFiles.length > availableSlots || validFiles.length !== selectedFiles.length) {
      setError(t("createListing.media.validation", { count: maxCount, size: "5 MB" }));
    } else {
      setError("");
    }

    // Uploads stay uncropped; cropping only ever happens for whichever photo is chosen as the cover.
    const newFiles = validFiles.slice(0, Math.max(availableSlots, 0)).map((file) => {
      const previewUrl = URL.createObjectURL(file);
      return {
        file,
        name: file.name,
        previewUrl,
        originalFile: file,
        originalPreviewUrl: previewUrl,
        isCropped: false,
      };
    });
    onChange([...files, ...newFiles]);
    event.target.value = "";
  };

  const requestCoverChange = (index) => {
    if (index === coverIndex) return;
    const target = files[index];
    setCropRequest({ index, imageSrc: target.originalPreviewUrl, fileName: target.originalFile.name });
  };

  const requestRecrop = () => {
    const target = files[coverIndex];
    if (!target) return;
    setCropRequest({ index: coverIndex, imageSrc: target.originalPreviewUrl, fileName: target.originalFile.name });
  };

  const handleCropSave = (croppedFile) => {
    const { index } = cropRequest;
    const previousCoverIndex = coverIndex;
    const nextFiles = files.map((item, itemIndex) => {
      if (itemIndex === index) {
        if (item.isCropped) URL.revokeObjectURL(item.previewUrl);
        return {
          ...item,
          file: croppedFile,
          name: croppedFile.name,
          previewUrl: URL.createObjectURL(croppedFile),
          isCropped: true,
        };
      }
      // Switching the cover to a different photo reverts the old cover back to its original, uncropped file.
      if (itemIndex === previousCoverIndex && item.isCropped) {
        URL.revokeObjectURL(item.previewUrl);
        return {
          ...item,
          file: item.originalFile,
          name: item.originalFile.name,
          previewUrl: item.originalPreviewUrl,
          isCropped: false,
        };
      }
      return item;
    });
    onChange(nextFiles);
    onCoverChange(index);
    setCropRequest(null);
  };

  const handleCropCancel = () => setCropRequest(null);

  const removeFile = (index) => {
    const removed = files[index];
    const nextFiles = files.filter((_, fileIndex) => fileIndex !== index);
    URL.revokeObjectURL(removed.previewUrl);
    if (removed.originalPreviewUrl !== removed.previewUrl) URL.revokeObjectURL(removed.originalPreviewUrl);
    onChange(nextFiles);
    if (coverIndex === index) onCoverChange(0);
    if (coverIndex > index) onCoverChange(coverIndex - 1);
  };

  return (
    <section className="listing-form-section">
      <h2 className="listing-form-section-title">{t("createListing.media.title")}</h2>
      <p className="listing-form-hint">{t("createListing.media.guidance", { count: maxCount, size: "5 MB" })}</p>
      {replacesExisting && <p className="listing-form-hint">{t("createListing.media.replaceHint")}</p>}
      <label className={`media-dropzone${hasReachedLimit ? " is-disabled" : ""}`} aria-disabled={hasReachedLimit}>
        <span className="media-dropzone-text">{t("createListing.media.upload")}</span>
        <input type="file" accept="image/*" multiple className="media-file-input" onChange={handleFileChange} disabled={hasReachedLimit} />
      </label>
      {error && <p role="alert" className="listing-form-error">{error}</p>}
      {files.length > 0 && (
        <>
          <p className="listing-form-hint">{t("createListing.media.selected", { count: files.length })}</p>
          <div className="media-grid">
            {files.map((file, index) => (
              <div key={`${file.name}-${index}`} className="media-item">
                <div className={`media-frame${coverIndex === index ? " is-cover" : ""}`}>
                  <img src={file.previewUrl} alt={file.name} className="media-preview" />
                  <button type="button" onClick={() => removeFile(index)} className="media-remove">{t("createListing.media.remove")}</button>
                </div>
                <label className="media-cover-option">
                  <input type="radio" name="cover-image" checked={coverIndex === index} onChange={() => requestCoverChange(index)} className="media-cover-radio" />
                  {t("createListing.media.cover")}
                </label>
                {coverIndex === index && (
                  <button type="button" onClick={requestRecrop} className="media-recrop">
                    {t(file.isCropped ? "createListing.media.crop.recrop" : "createListing.media.crop.cropCover")}
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      {cropRequest && (
        <ImageCropModal
          key={cropRequest.imageSrc}
          imageSrc={cropRequest.imageSrc}
          fileName={cropRequest.fileName}
          aspect={COVER_ASPECT_RATIO}
          onCancel={handleCropCancel}
          onSave={handleCropSave}
        />
      )}
    </section>
  );
}
