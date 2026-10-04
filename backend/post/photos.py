"""Cleaning uploaded listing photos before they are stored, and the small copies listing cards show."""
import io
from urllib.parse import urlsplit

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

JPEG_QUALITY = 90

# Listing cards show a small copy of the cover photo, so a page of results doesn't download every
# seller's full-size camera photo; the listing page still shows the originals. Fitting in 640px covers
# the widest card (~320px) on a 2x screen. WebP keeps transparency and is about a third smaller than JPEG.
THUMBNAIL_SIZE = (640, 640)
THUMBNAIL_QUALITY = 80
THUMBNAIL_SUFFIX = '.thumb.webp'

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


def photo_folder(post):
    """Where a listing's uploaded photos are stored, so they can all be removed with the listing."""
    return f'listings/{post._meta.model_name}/{post.pk}'


def delete_photo_folder(folder):
    try:
        _, files = default_storage.listdir(folder)
    except FileNotFoundError:
        return
    for name in files:
        default_storage.delete(f'{folder}/{name}')


def stored_name(url):
    """The storage name of a photo this app stored (under MEDIA_URL), or None for any other URL."""
    media = urlsplit(settings.MEDIA_URL)
    parts = urlsplit(url or '')
    if media.netloc and parts.netloc != media.netloc:
        return None
    if not parts.path.startswith(media.path):
        return None
    return parts.path[len(media.path):] or None


def thumbnail_name(name):
    """Where the card-sized copy of the stored photo `name` goes: next to it, so it's deleted with the listing."""
    return f'{name.rsplit(".", 1)[0]}{THUMBNAIL_SUFFIX}'


def make_thumbnail(source):
    """Returns a ContentFile with a WebP copy of the image file `source`, shrunk to fit THUMBNAIL_SIZE."""
    with Image.open(source) as original:
        original.draft('RGB', THUMBNAIL_SIZE)  # lets JPEG decode at a smaller scale, saving memory
        # Kept so phone photos (often Display P3) don't come out duller than the original.
        icc_profile = original.info.get('icc_profile')
        image = original.convert('RGBA' if original.mode in ('RGBA', 'LA', 'P') else 'RGB')
    image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    options = {'icc_profile': icc_profile} if icc_profile else {}
    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=THUMBNAIL_QUALITY, method=6, **options)
    return ContentFile(buffer.getvalue())


def save_thumbnail(name, source=None):
    """
    Stores the card-sized copy of the stored photo `name` (read from `source` if given, else from
    storage) and returns its storage name. Photos are stripped of metadata before they're stored, so
    the copy carries none either.
    """
    target = thumbnail_name(name)
    if source is None:
        with default_storage.open(name) as stored:
            content = make_thumbnail(stored)
    else:
        source.seek(0)
        content = make_thumbnail(source)
    # Saving over an existing file would give it another name instead of replacing it.
    if default_storage.exists(target):
        default_storage.delete(target)
    return default_storage.save(target, content)


def refresh_thumbnail(post, build_url, sources=None):
    """
    Points `post.thumbnail` at a card-sized copy of its current cover photo, making the copy if it's
    missing. Covers this app didn't store (the demo data's hot-linked photos) get no copy; cards fall
    back to the cover itself. `build_url` turns a storage name into the URL to save; `sources` maps a
    cover URL to its file when it was just uploaded. Doesn't save `post`; returns the storage name of
    the copy it replaced (to delete once the listing is saved), or None.
    """
    old_name = stored_name(post.thumbnail)
    cover_name = stored_name(post.image)
    wanted = thumbnail_name(cover_name) if cover_name else None
    if not cover_name:
        post.thumbnail = ''
    elif old_name != wanted or not default_storage.exists(wanted):
        post.thumbnail = build_url(save_thumbnail(cover_name, (sources or {}).get(post.image)))
    return old_name if old_name and old_name != wanted else None
