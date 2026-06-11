# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from api.auth import EncomiendaTokenView

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenBlacklistView,
)

from envios import views_auth

urlpatterns = [
    # ───────────────── ADMIN ─────────────────
    path('admin/', admin.site.urls),

    # ───────────────── API VERSIONADA ─────────────────
    # Ahora sí soporta:
    # /api/v1/...
    # /api/v2/...
    
    path('api/<str:version>/', include('api.urls')),
    # ───────────────── API VERSIONADA ─────────────────
    # Ahora SÍ captura el parámetro y se lo pasa a Django REST Framework
    

    # ───────────────── DOCUMENTACIÓN ─────────────────
    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger'
    ),

    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),

    # ───────────────── APP WEB ENVÍOS ─────────────────
    path('', include('envios.urls')),

    # ───────────────── AUTENTICACIÓN WEB ─────────────────
    path('accounts/login/', views_auth.login_view),
    path('accounts/logout/', views_auth.logout_view),

    path(
        'accounts/',
        include('django.contrib.auth.urls')
    ),

    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('perfil/', views_auth.perfil_view, name='perfil'),

    # ───────────────── JWT ─────────────────
    path(
        'api/v1/auth/token/',
        EncomiendaTokenView.as_view(),
        name='token_obtain'
    ),

    path(
        'api/v1/auth/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    path(
        'api/v1/auth/token/blacklist/',
        TokenBlacklistView.as_view(),
        name='token_blacklist'
    ),
]

# ───────────────── STATIC Y MEDIA ─────────────────
if settings.DEBUG:
    from silk import urls as silk_urls

    urlpatterns += [
        path('silk/', include('silk.urls', namespace='silk')),
    ]

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

# ───────────────── PERSONALIZACIÓN ADMIN ─────────────────
admin.site.site_header = 'Sistema de Gestión de Encomiendas'
admin.site.site_title = 'Encomiendas Admin'
admin.site.index_title = 'Panel de Administración'
