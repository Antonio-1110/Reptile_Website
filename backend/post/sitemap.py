"""
/sitemap.xml: every public page worth finding in a search engine, so Google learns about new listings
without having to crawl the whole single-page app. Links point at the frontend (FRONTEND_URL); the
frontend's host proxies its own /sitemap.xml here (Frontend/vercel.json), since a sitemap is only
trusted for URLs on the host that serves it.
"""
from xml.sax.saxutils import escape

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from account.models import Account
from .models import BasePost, EquipmentPost, LiveAnimalPost

# Pages anyone can see that don't depend on a listing; the private ones are in Frontend/public/robots.txt.
STATIC_PAGES = ('/', '/marketplace', '/auctions')

# Sold listings keep their page (see BasePost.Status) but are left out: nobody searching can buy them.
FOR_SALE = ~Q(status=BasePost.Status.SOLD)


def _url(path, lastmod=None):
    entry = f'<url><loc>{escape(settings.FRONTEND_URL + path)}</loc>'
    if lastmod:
        entry += f'<lastmod>{lastmod.date().isoformat()}</lastmod>'
    return entry + '</url>'


@require_GET
@cache_page(60 * 60)
def sitemap(request):
    live_animals = LiveAnimalPost.objects.filter(LiveAnimalPost.PUBLISHED, FOR_SALE)
    equipment = EquipmentPost.objects.filter(is_hidden=False).filter(FOR_SALE)
    sellers = Account.objects.filter(
        Q(id__in=live_animals.values('account')) | Q(id__in=equipment.values('account'))
    )
    entries = [_url(path) for path in STATIC_PAGES]
    entries += [_url(f'/posts/{pk}', updated) for pk, updated in live_animals.values_list('id', 'updated_at')]
    entries += [_url(f'/equipment/{pk}', updated) for pk, updated in equipment.values_list('id', 'updated_at')]
    entries += [_url(f'/sellers/{pk}') for pk in sellers.values_list('id', flat=True)]
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(entries)
        + '\n</urlset>\n'
    )
    return HttpResponse(body, content_type='application/xml')
