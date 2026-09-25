function createImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", (error) => reject(error));
    image.setAttribute("crossOrigin", "anonymous");
    image.src = url;
  });
}

function toJpegFileName(originalName) {
  const base = originalName.replace(/\.[^/.]+$/, "").trim();
  return `${base || "cover"}.jpg`;
}

/**
 * Draws the cropped region of an image onto a canvas and returns it as a JPEG File,
 * so listing cover photos can be uploaded with a consistent MIME type regardless of source format.
 * @param {string} imageSrc object URL or data URL of the source image
 * @param {{ x: number, y: number, width: number, height: number }} pixelCrop crop rect in source pixels
 * @param {string} [originalName] used to derive the output filename
 * @returns {Promise<File>}
 */
export async function getCroppedImg(imageSrc, pixelCrop, originalName = "cover.jpg") {
  const image = await createImage(imageSrc);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  if (!ctx) throw new Error("Canvas 2D context is not available.");

  canvas.width = pixelCrop.width;
  canvas.height = pixelCrop.height;

  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Canvas is empty."));
          return;
        }
        resolve(new File([blob], toJpegFileName(originalName), { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.92,
    );
  });
}
