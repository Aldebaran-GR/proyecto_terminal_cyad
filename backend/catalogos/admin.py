from django.contrib import admin

from .models import Area, Departamento, Licenciatura, Periodo, Posgrado, UEA


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "estado")
    search_fields = ("clave", "nombre")
    list_filter = ("estado",)


@admin.register(Licenciatura)
class LicenciaturaAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "orden", "departamento", "estado")
    list_editable = ("orden",)
    list_filter = ("estado", "departamento")
    search_fields = ("clave", "nombre")
    ordering = ("orden", "nombre")


@admin.register(Posgrado)
class PosgradoAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "orden", "departamento", "estado")
    list_editable = ("orden",)
    list_filter = ("estado", "departamento")
    search_fields = ("clave", "nombre")
    ordering = ("orden", "nombre")


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "estado")
    search_fields = ("nombre", "descripcion")
    list_filter = ("estado",)


@admin.register(UEA)
class UEAAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "programa", "area", "trimestre", "tipo", "estado")
    list_filter = ("licenciatura", "posgrado", "area", "tipo", "estado")
    search_fields = ("clave", "nombre")

    @admin.display(description="Programa")
    def programa(self, obj):
        return obj.licenciatura or obj.posgrado


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = (
        "clave", "fecha_inicio", "fecha_fin",
        "activo_cartas", "activo_requisitos", "activo_autoevaluacion",
        "estado",
    )
    list_filter = (
        "activo_cartas", "activo_requisitos", "activo_autoevaluacion", "estado",
    )
