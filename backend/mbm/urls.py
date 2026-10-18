from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from transit import views, demo_views, catalogue
from transit.sptrans import views as sptrans
from transit.sptrans.compact import catalogue as stop_catalogue
from transit.sptrans.addresses import suggestions

urlpatterns = [
    path("api/sptrans/stop-catalogue/", stop_catalogue),
    path("api/location-config/", views.location_config),
    path("api/sptrans/stops/", sptrans.stops),
    path("api/sptrans/addresses/", suggestions),
    path("api/sptrans/destination/", sptrans.destination),
    path("api/sptrans/board/", sptrans.board),
    path("api/sptrans/walk/", sptrans.walk),
    path("api/sptrans/trips/<str:trip_id>/", sptrans.trip),
    path("api/sptrans/qr/<str:stop_id>/", sptrans.qr),
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
