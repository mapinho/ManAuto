from django.contrib import admin

from .models import EventoPreventiva, PlanoAnual


class EventoPreventivaInline(admin.TabularInline):
    model = EventoPreventiva
    extra = 0
    fields = ("data", "ativo", "tipo", "hh", "oficina", "responsavel", "status_execucao")


@admin.register(PlanoAnual)
class PlanoAnualAdmin(admin.ModelAdmin):
    list_display = ("conjunto_premissas", "status", "organizacao", "criado_em")
    list_filter = ("organizacao", "status")
    inlines = [EventoPreventivaInline]


@admin.register(EventoPreventiva)
class EventoPreventivaAdmin(admin.ModelAdmin):
    list_display = ("ativo", "tipo", "data", "hh", "oficina", "responsavel", "status_execucao")
    list_filter = ("organizacao", "tipo", "oficina", "status_execucao")
    date_hierarchy = "data"
    search_fields = ("ativo__nome",)
