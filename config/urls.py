from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.BRAND_NAME} admin"
admin.site.site_title = settings.BRAND_NAME

# media comes before the store so /media/... isn't swallowed by the /<department>/ route
urlpatterns = [
    path("admin/", admin.site.urls),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    path("", include("store.urls")),
]

handler400 = "store.views_care.bad_request"
handler403 = "store.views_care.permission_denied"
handler404 = "store.views_care.page_not_found"
handler500 = "store.views_care.server_error"
