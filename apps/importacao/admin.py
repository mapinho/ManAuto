from django.contrib import admin

from .models import OrdemServico


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = (
        "id_externo",
        "ativo",
        "data",
        "tipo_os",
        "oficina",
        "custo_total",
        "organizacao",
    )
    list_filter = ("organizacao", "tipo_os", "oficina")
    date_hierarchy = "data"
    search_fields = ("ativo__nome", "sistema_falha", "id_externo")
