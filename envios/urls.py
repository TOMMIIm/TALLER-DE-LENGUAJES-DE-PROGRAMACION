from django.urls import path
from . import views_cbv
from . import views

urlpatterns = [
    path('', views_cbv.EncomiendaListView.as_view(), name='encomienda_lista'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('<int:pk>/', views_cbv.EncomiendaDetailView.as_view(), name='encomienda_detalle'),
    path('nueva/', views_cbv.EncomiendaCreateView.as_view(), name='encomienda_crear'),
    path('<int:pk>/editar/', views_cbv.EncomiendaUpdateView.as_view(), name='encomienda_editar'),
]
