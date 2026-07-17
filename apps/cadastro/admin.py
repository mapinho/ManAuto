from django.contrib import admin

from .models import (
    AtividadeMaterial,
    Ativo,
    ChecklistAtividade,
    ClasseAtivo,
    Gatilho,
    ItemMaterial,
    MedicaoUso,
    Oficina,
    Pessoa,
)


class GatilhoInline(admin.TabularInline):
    model = Gatilho
    extra = 1


@admin.register(Oficina)
class OficinaAdmin(admin.ModelAdmin):
    list_display = ("nome", "organizacao", "prev_pct", "corr_pct", "deflator_pct", "terceiros_pct")
    list_filter = ("organizacao",)
    search_fields = ("nome",)


@admin.register(ClasseAtivo)
class ClasseAtivoAdmin(admin.ModelAdmin):
    list_display = ("nome", "organizacao", "unidade")
    list_filter = ("organizacao", "unidade")
    search_fields = ("nome",)
    inlines = [GatilhoInline]


@admin.register(Ativo)
class AtivoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "classe",
        "status",
        "tipo_gatilho",
        "uso_atual",
        "id_externo",
        "organizacao",
    )
    list_filter = ("organizacao", "classe", "status")
    search_fields = ("nome", "modelo", "fabricante", "id_externo")


@admin.register(MedicaoUso)
class MedicaoUsoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "data", "valor")
    list_filter = ("organizacao",)
    date_hierarchy = "data"


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    # Salario/encargos ficam fora da listagem por padrao: acesso restrito
    # ainda depende de permissao dedicada + criptografia pgcrypto (nao
    # implementadas neste passo — ver SPEC_Tecnica_Ambiente.md SS5).
    list_display = ("nome", "cargo", "oficina", "turno", "status", "id_externo", "organizacao")
    list_filter = ("organizacao", "oficina", "turno", "status")
    search_fields = ("nome", "cargo", "id_externo")


@admin.register(ChecklistAtividade)
class ChecklistAtividadeAdmin(admin.ModelAdmin):
    list_display = (
        "classe",
        "tipo_prev",
        "oficina",
        "descricao",
        "hh",
        "id_checklist",
        "organizacao",
    )
    list_filter = ("organizacao", "classe", "tipo_prev", "oficina")
    search_fields = ("descricao", "id_checklist", "id_externo")


@admin.register(ItemMaterial)
class ItemMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "tipo",
        "unidade",
        "custo_unitario",
        "id_externo",
        "organizacao",
    )
    list_filter = ("organizacao", "tipo")
    search_fields = ("descricao", "id_externo", "codigo_fabricante")


@admin.register(AtividadeMaterial)
class AtividadeMaterialAdmin(admin.ModelAdmin):
    list_display = ("atividade", "item", "qtd", "unidade")
    list_filter = ("organizacao",)
