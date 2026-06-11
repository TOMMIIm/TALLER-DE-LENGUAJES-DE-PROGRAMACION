from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import EncomiendaViewSet
from . import views

router = DefaultRouter()
router.register(r'encomiendas', EncomiendaViewSet, basename='encomienda')

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('web/encomiendas/', views.encomienda_lista, name='encomienda_lista'),
    path('web/encomiendas/nueva/', views.encomienda_crear, name='encomienda_crear'),
    path('web/encomiendas/<int:pk>/', views.encomienda_detalle, name='encomienda_detalle'),
    path(
        'web/encomiendas/<int:pk>/cambiar-estado/',
        views.encomienda_cambiar_estado,
        name='encomienda_cambiar_estado'
    ),
    path('', include(router.urls)),
]
