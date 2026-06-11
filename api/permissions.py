from rest_framework.permissions import BasePermission

from envios.models import Empleado


class EsEmpleadoActivo(BasePermission):
    """Solo empleados activos del sistema pueden acceder"""

    message = 'Solo empleados activos tienen acceso a esta API.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        empleado = Empleado.objects.filter(
            email=request.user.email
        ).first()
        return empleado is None or empleado.estado == 1


class EsPropietarioOAdmin(BasePermission):
    """El usuario puede ver/editar solo sus propias encomiendas, a menos que sea admin"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.empleado_registro.email == request.user.email
