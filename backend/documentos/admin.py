from django.contrib import admin

from .models import (
    Bibliografia, CartaTematica, CriterioEvaluacion,
    RequisitoItem, RequisitoRecuperacion, Subtema, Tema,
)


class TemaInline(admin.TabularInline):
    model = Tema
    extra = 0


class BibliografiaInline(admin.TabularInline):
    model = Bibliografia
    extra = 0


class CriterioInline(admin.TabularInline):
    model = CriterioEvaluacion
    extra = 0


@admin.register(CartaTematica)
class CartaTematicaAdmin(admin.ModelAdmin):
    list_display = ("id", "profesor", "uea", "periodo", "nombre_grupo", "estado", "created_at")
    list_filter = ("estado", "periodo", "uea__licenciatura")
    search_fields = ("nombre_grupo", "id_grupo", "uea__nombre", "profesor__nombre_completo")
    inlines = [TemaInline, BibliografiaInline, CriterioInline]
    raw_id_fields = ("profesor", "uea", "periodo")


class RequisitoItemInline(admin.TabularInline):
    model = RequisitoItem
    extra = 0


@admin.register(RequisitoRecuperacion)
class RequisitoRecuperacionAdmin(admin.ModelAdmin):
    list_display = ("id", "profesor", "uea", "periodo", "nombre_grupo", "estado", "created_at")
    list_filter = ("estado", "periodo", "uea__licenciatura")
    search_fields = ("nombre_grupo", "id_grupo", "uea__nombre", "profesor__nombre_completo")
    inlines = [RequisitoItemInline]
    raw_id_fields = ("profesor", "uea", "periodo")
