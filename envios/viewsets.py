from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.core.cache import cache

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiTypes,
)

from api.filters import EncomiendaFilter
from api.exceptions import EstadoInvalidoError, EncomiendaYaEntregadaError
from api.pagination import EncomiendaPagination, HistorialPagination
from api.permissions import EsEmpleadoActivo, EsPropietarioOAdmin
from api.throttles import EmpleadoRateThrottle, CambioEstadoThrottle
from config.settings import CACHE_TTL

from .models import Encomienda, Empleado

from .serializers import (
    EncomiendaSerializer,
    EncomiendaListSerializer,
    EncomiendaDetailSerializer,
    EncomiendaV2Serializer,
    HistorialEstadoSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Encomiendas']),
    create=extend_schema(tags=['Encomiendas']),
    retrieve=extend_schema(tags=['Encomiendas']),
)
class EncomiendaViewSet(viewsets.ModelViewSet):

    queryset = Encomienda.objects.con_relaciones()
    pagination_class = EncomiendaPagination

    permission_classes = [EsEmpleadoActivo]
    throttle_classes = [EmpleadoRateThrottle]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = EncomiendaFilter

    search_fields = [
        'codigo',
        'descripcion',
        'remitente__apellidos',
        'destinatario__apellidos',
    ]

    ordering_fields = [
        'fecha_registro',
        'peso_kg',
        'costo_envio',
    ]

    ordering = ['-fecha_registro']

    # =========================
    # VERSION HEADER SAFE
    # =========================
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        version = getattr(request, 'version', None)
        if version:
            response['X-API-Version'] = version

        return response

    # =========================
    # PERMISSIONS
    # =========================
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [EsEmpleadoActivo(), EsPropietarioOAdmin()]

        return [EsEmpleadoActivo()]

    def get_throttles(self):
        if self.action == 'cambiar_estado':
            return [CambioEstadoThrottle()]
        return super().get_throttles()

    # =========================
    # SERIALIZERS (VERSIONES)
    # =========================
    def get_serializer_class(self):
        if self.action == 'list':
            return EncomiendaListSerializer

        if 'v2' in self.request.path:
            return EncomiendaV2Serializer

        if self.action == 'retrieve':
            return EncomiendaDetailSerializer

        return EncomiendaSerializer

    def get_queryset(self):
        """
        Todas las acciones del ViewSet pasan por aqui.
        Siempre empezamos con con_relaciones() para evitar N+1.
        Los filtros adicionales se aplican encima.
        """
        qs = Encomienda.objects.con_relaciones()

        if self.action == 'list':
            qs = qs.only(
                'id', 'codigo', 'estado',
                'peso_kg', 'costo_envio',
                'fecha_registro', 'fecha_entrega_est',
                'empleado_registro',
                'remitente__nombres', 'remitente__apellidos',
                'destinatario__nombres', 'destinatario__apellidos',
                'ruta__destino',
            )

        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        q = self.request.query_params.get('search')
        if q:
            qs = qs.filter(
                Q(codigo__icontains=q) |
                Q(remitente__apellidos__icontains=q) |
                Q(destinatario__apellidos__icontains=q)
            )

        return qs

    def _get_empleado_from_user(self):
        return Empleado.objects.filter(
            email=self.request.user.email
        ).first()

    # =========================
    # CREATE
    # =========================
    def perform_create(self, serializer):
        empleado = self._get_empleado_from_user()
        if empleado is None:
            raise serializers.ValidationError(
                {'empleado_registro': 'Empleado no encontrado'}
            )

        serializer.save(
            empleado_registro=empleado
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache_key = f'estadisticas_empleado_{self.request.user.id}'
        cache.delete(cache_key)

    # =========================
    # CAMBIAR ESTADO (TEST FIX)
    # =========================
    @action(
        detail=True,
        methods=['post'],
        url_path='cambiar-estado',
        url_name='cambiar-estado'
    )
    def cambiar_estado(self, request, pk=None):

        enc = self.get_object()
        if enc.esta_entregada:
            raise EncomiendaYaEntregadaError()

        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        if not nuevo_estado:
            return Response(
                {'error': 'estado requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empleado = Empleado.objects.filter(
                email=request.user.email
            ).first()

            if not empleado:
                return Response(
                    {'error': 'Empleado no encontrado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            enc.cambiar_estado(
                nuevo_estado,
                empleado,
                observacion
            )

            cache.delete_many([
                f'estadisticas_empleado_{request.user.id}',
                f'encomienda_detalle_{pk}',
            ])

            serializer = self.get_serializer(enc)
            return Response(serializer.data)

        except ValueError as e:
            raise EstadoInvalidoError(detail=str(e))

    # =========================
    # CON RETRASO
    # =========================
    @action(detail=False, methods=['get'], url_path='con-retraso')
    def con_retraso(self, request):

        qs = Encomienda.objects.con_retraso().con_relaciones()

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # =========================
    # PENDIENTES
    # =========================
    @action(detail=False, methods=['get'], url_path='pendientes')
    def pendientes(self, request):

        qs = Encomienda.objects.pendientes().con_relaciones()

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # =========================
    # HISTORIAL
    # =========================
    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None):

        enc = self.get_object()

        qs = enc.historial.select_related('empleado').order_by('-fecha_cambio')

        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = HistorialEstadoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = HistorialEstadoSerializer(qs, many=True)
        return Response(serializer.data)

    # =========================
    # ESTADISTICAS
    # =========================
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        from django.utils import timezone
        cache_key = f'estadisticas_empleado_{request.user.id}'
        data = cache.get(cache_key)

        if data is None:
            data = {
                'activas': Encomienda.objects.activas().count(),
                'en_transito': Encomienda.objects.en_transito().count(),
                'con_retraso': Encomienda.objects.con_retraso().count(),
                'entregadas_mes': Encomienda.objects.filter(
                    estado='EN',
                    fecha_entrega_real__month=timezone.now().month
                ).count(),
            }
            cache.set(cache_key, data, CACHE_TTL)

        return Response(data)

    @extend_schema(
        summary='Crear multiples encomiendas',
        description='Crea varias encomiendas en una sola peticion. Body: lista de objetos.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request, version=None):
        """
        POST /api/v1/encomiendas/bulk_create/
        Body: [{enc1}, {enc2}, {enc3}]
        Crea todas las encomiendas con una sola query SQL.
        """
        serializer = self.get_serializer(
            data=request.data, many=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        empleado = Empleado.objects.get(email=request.user.email)
        encomiendas = serializer.save(empleado_registro=empleado)
        return Response(
            self.get_serializer(encomiendas, many=True).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary='Cambiar estado a multiples encomiendas',
        description='Cambia el estado de varias encomiendas. Reporta cuales tuvieron errores.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['patch'], url_path='bulk_estado')
    def bulk_estado(self, request, version=None):
        """
        PATCH /api/v1/encomiendas/bulk_estado/
        Body: {"ids": [1, 2, 3], "estado": "TR", "observacion": "..."}
        Procesa cada encomienda y reporta cuales tuvieron errores.
        """
        ids = request.data.get('ids', [])
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        if not ids:
            return Response(
                {'error': 'El campo ids es requerido y no puede estar vacio.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empleado = Empleado.objects.get(email=request.user.email)
        except Empleado.DoesNotExist:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado.'},
                status=status.HTTP_403_FORBIDDEN
            )

        encomiendas = Encomienda.objects.filter(id__in=ids)
        actualizadas = []
        errores = []

        for enc in encomiendas:
            try:
                enc.cambiar_estado(nuevo_estado, empleado, observacion)
                actualizadas.append(enc.id)
            except ValueError as e:
                errores.append({'id': enc.id, 'error': str(e)})

        ids_procesados = list(encomiendas.values_list('id', flat=True))
        no_encontrados = [i for i in ids if i not in ids_procesados]

        return Response({
            'actualizadas': actualizadas,
            'errores': errores,
            'no_encontrados': no_encontrados,
            'total': len(actualizadas),
        })
