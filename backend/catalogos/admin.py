from django.contrib import admin

from .models import Departamento, Licenciatura, Periodo, UEA


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "estado")
    search_fields = ("clave", "nombre")
    list_filter = ("estado",)


@admin.register(Licenciatura)
class LicenciaturaAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "departamento", "estado")
    list_filter = ("estado", "departamento")
    search_fields = ("clave", "nombre")


@admin.register(UEA)
class UEAAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "licenciatura", "trimestre", "tipo", "estado")
    list_filter = ("licenciatura", "tipo", "etapa", "estado")
    search_fields = ("clave", "nombre")


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ("clave", "fecha_inicio", "fecha_fin", "activo", "estado")
    list_filter = ("activo", "estado")
