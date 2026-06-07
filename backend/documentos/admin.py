from django.contrib import admin

from .models import CartaTematica, RequisitoRecuperacion


@admin.register(CartaTematica)
class CartaTematicaAdmin(admin.ModelAdmin):
    list_display = ("id", "profesor", "uea", "periodo", "nombre_grupo", "estado", "created_at")
    list_filter = ("estado", "periodo", "uea__licenciatura")
    search_fields = ("nombre_grupo", "id_grupo", "uea__nombre", "profesor__nombre_completo")
    raw_id_fields = ("profesor", "uea", "periodo")


@admin.register(RequisitoRecuperacion)
class RequisitoRecuperacionAdmin(admin.ModelAdmin):
    list_display = ("id", "profesor", "uea", "periodo", "nombre_grupo", "estado", "created_at")
    list_filter = ("estado", "periodo", "uea__licenciatura")
    search_fields = ("nombre_grupo", "id_grupo", "uea__nombre", "profesor__nombre_completo")
    raw_id_fields = ("profesor", "uea", "periodo")
