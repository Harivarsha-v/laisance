from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from store.sitemaps import SITEMAPS

ROBOTS = """User-agent: *
Disallow: /admin/
Disallow: /api/
Disallow: /bag/
Disallow: /checkout/
Disallow: /account/
Disallow: /order/
Disallow: /search/
Disallow: /currency/
Sitemap: {sitemap}
"""


def robots_txt(request):
    return HttpResponse(ROBOTS.format(sitemap=request.build_absolute_uri("/sitemap.xml")), content_type="text/plain")


admin.site.site_header = f"{settings.BRAND_NAME} admin"
admin.site.site_title = settings.BRAND_NAME

# media comes before the store so /media/... isn't swallowed by the /<department>/ route
urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    path("", include("store.urls")),
]

handler400 = "store.views_care.bad_request"
handler403 = "store.views_care.permission_denied"
handler404 = "store.views_care.page_not_found"
handler500 = "store.views_care.server_error"
