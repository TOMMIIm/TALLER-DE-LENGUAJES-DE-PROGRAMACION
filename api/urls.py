from django.urls import path, include

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from envios import api_views
from envios.viewsets import EncomiendaViewSet


# =========================
# ROUTER
# =========================

router = DefaultRouter()

router.register(
    'encomiendas',
    EncomiendaViewSet,
    basename='encomiendas'
)


urlpatterns = [

    # =========================
    # CLIENTES Y RUTAS
    # =========================

    path(
        'clientes/',
        api_views.ClienteListView.as_view()
    ),

    path(
        'rutas/',
        api_views.RutaListView.as_view()
    ),

    # =========================
    # DOCUMENTACION
    # =========================

    path(
        'schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    path(
        'docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema'
        ),
        name='swagger'
    ),

    # =========================
    # API
    # =========================

    path(
        '',
        include(router.urls)
    ),
]