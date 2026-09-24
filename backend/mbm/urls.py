from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from transit import views, demo_views, catalogue

urlpatterns = [
    path("api/catalogue/", catalogue.catalogue),
    path("api/catalogue/routes/<str:route_id>/", catalogue.route_detail),
    path("api/network/", demo_views.network),
    path("api/board/", demo_views.board),
    path("api/journey/", demo_views.journey),
    path("explorar/", views.index),
    path("admin/", admin.site.urls),
    path("api/demo/network/", demo_views.network),
    path("api/demo/stops/<str:stop_id>/", demo_views.stop),
    path("api/demo/board/", demo_views.board),
    path("api/demo/journey/", demo_views.journey),
    path("api/demo/qr/<str:stop_id>/", demo_views.qr),
    path("api/demo/evaluation/", demo_views.evaluation),
    path("api/health/", views.health),
    path("api/geocode/", views.geocode),
    path("api/nearby/", views.nearby),
    path("", views.index),
] + static("/assets/", document_root=settings.BASE_DIR / "frontend/dist/assets")
