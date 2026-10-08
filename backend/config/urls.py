from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health"),
    # API versionada
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.tickets.urls")),
    # Documentação OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[]), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[]),
        name="swagger-ui",
    ),
]
