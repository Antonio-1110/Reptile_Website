// Items in the listing editor's photo list: new uploads and photos the listing already has.

let nextItemId = 0;
export const newItemId = () => {
  nextItemId += 1;
  return nextItemId;
};

export const isBlobUrl = (url) => typeof url === "string" && url.startsWith("blob:");

// A photo the listing already has, shown next to new uploads so it can be kept, moved or removed.
// It has no File: the cover crop tool can't read images from another origin, so an existing photo
// becomes the cover as it is.
export function existingPhoto(url) {
  const last = url.split("/").pop().split("?")[0];
  let name = last;
  try {
    name = decodeURIComponent(last);
  } catch {
    // A malformed escape: show the raw file name.
  }
  return { id: newItemId(), existingUrl: url, name: name || url, previewUrl: url, originalPreviewUrl: url, isCropped: false, file: null, originalFile: null };
}
