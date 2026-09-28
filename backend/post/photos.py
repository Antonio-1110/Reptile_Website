"""Cleaning uploaded listing photos before they are stored."""
import io

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

JPEG_QUALITY = 90

# Output format for each input format; anything else (GIF, BMP, TIFF, …) is stored as PNG, which keeps
# transparency without loss.
SAVE_AS = {'JPEG': 'JPEG', 'MPO': 'JPEG', 'WEBP': 'WEBP'}
EXTENSIONS = {'JPEG': '.jpg', 'WEBP': '.webp', 'PNG': '.png'}


def without_metadata(upload):
    """
    Returns `(ContentFile, extension)`: the photo re-encoded with no EXIF, XMP or comments.

    Phone photos usually carry the GPS position they were taken at (often the seller's home), and listing
    photos are public, so nothing but the pixels (and the colour profile) may be kept. The EXIF
    orientation is applied to the pixels first, so the photo stays the right way up once the tag is gone.
    Only the first frame of an animated or multi-picture file is kept.

    Raises OSError or ValueError for an image Pillow can't decode or convert.
    """
    upload.seek(0)
    with Image.open(upload) as original:
        fmt = SAVE_AS.get(original.format, 'PNG')
        icc_profile = original.info.get('icc_profile')
        image = ImageOps.exif_transpose(original)

    if fmt == 'JPEG' and image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')
    elif fmt != 'JPEG' and image.mode not in ('RGB', 'RGBA', 'L', 'LA'):
        # Before `info` is cleared: a palette image's transparency lives there.
        image = image.convert('RGBA')
    # The savers copy some metadata (JPEG and GIF comments) straight from `info`, so empty it.
    image.info = {}

    options = {'icc_profile': icc_profile} if icc_profile else {}
    if fmt in ('JPEG', 'WEBP'):
        options['quality'] = JPEG_QUALITY
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **options)
    return ContentFile(buffer.getvalue()), EXTENSIONS[fmt]
