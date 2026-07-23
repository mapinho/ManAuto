from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include("config.api_urls")),
    path("", include("apps.core.urls")),
    path("<slug:org_slug>/premissas/", include("apps.premissas.urls")),
    path("<slug:org_slug>/", include("apps.cadastro.urls")),
    path("<slug:org_slug>/cronograma/", include("apps.plano.urls")),
]
