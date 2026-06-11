from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from api.pagination import ClientePagination
from config.settings import CACHE_TTL
from .models import Encomienda
from clientes.models import Cliente
from rutas.models import Ruta
from .serializers import (
    EncomiendaSerializer,
    EncomiendaDetailSerializer,
    EncomiendaV2Serializer,
    ClienteSerializer,
    RutaSerializer,
)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def encomienda_list(request):
    if request.method == 'GET':
        qs = Encomienda.objects.con_relaciones()
        serializer = EncomiendaSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = EncomiendaSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(
                empleado_registro=request.user.empleado
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def encomienda_detail(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)

    if request.method == 'GET':
        return Response(EncomiendaSerializer(enc).data)

    elif request.method in ['PUT', 'PATCH']:
        s = EncomiendaSerializer(
            enc,
            data=request.data,
            partial=(request.method == 'PATCH')
        )

        if s.is_valid():
            s.save()
            return Response(s.data)

        return Response(s.errors, status=400)

    elif request.method == 'DELETE':
        enc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EncomiendaListAPIView(APIView):
    """GET /api/v1/encomiendas/ POST /api/v1/encomiendas/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Encomienda.objects.con_relaciones()

        serializer = EncomiendaSerializer(
            qs,
            many=True,
            context={'request': request}
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = EncomiendaSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save(
                empleado_registro=request.user.empleado
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class EncomiendaDetailAPIView(APIView):
    """GET/PUT/PATCH/DELETE /api/v1/encomiendas/{pk}/"""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Encomienda.objects.con_relaciones(),
            pk=pk
        )

    def get(self, request, pk):
        enc = self.get_object(pk)
        return Response(EncomiendaDetailSerializer(enc).data)

    def put(self, request, pk):
        enc = self.get_object(pk)

        s = EncomiendaSerializer(
            enc,
            data=request.data,
            context={'request': request}
        )

        if s.is_valid():
            s.save()
            return Response(s.data)

        return Response(s.errors, status=400)

    def patch(self, request, pk):
        enc = self.get_object(pk)

        s = EncomiendaSerializer(
            enc,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if s.is_valid():
            s.save()
            return Response(s.data)

        return Response(s.errors, status=400)

    def delete(self, request, pk):
        enc = self.get_object(pk)
        enc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================
# API V1
# =========================

class EncomiendaListCreateView(generics.ListCreateAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            empleado_registro=self.request.user.empleado
        )


class EncomiendaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Usar serializer diferente segun el metodo"""

        if self.request.method == 'GET':
            return EncomiendaDetailSerializer

        return EncomiendaSerializer


# =========================
# API V2
# =========================

class EncomiendaV2ListView(generics.ListCreateAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaV2Serializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            empleado_registro=self.request.user.empleado
        )


class EncomiendaV2DetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaV2Serializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    summary='Listar clientes activos',
    description='Devuelve todos los clientes con estado Activo, paginados de 20 en 20.',
    tags=['Clientes'],
)
class ClienteListView(generics.ListAPIView):
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ClientePagination

    def get_queryset(self):
        return Cliente.objects.activos()


@extend_schema(
    summary='Listar rutas activas',
    description='Devuelve todas las rutas con estado Activo. Sin paginacion.',
    tags=['Rutas'],
)
class RutaListView(generics.ListAPIView):
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @method_decorator(cache_page(CACHE_TTL))
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Ruta.objects.activas()
