from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from bulkmailing.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("clients/", include("clients.urls", namespace="clients")),
    path("texts/", include("texts.urls", namespace="texts")),
    path("bulkmailing/", include("bulkmailing.urls", namespace="bulkmailing")),
    path("statistics/", include("statistics.urls", namespace="statistics")),
    path("users/", include("users.urls", namespace="users")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
