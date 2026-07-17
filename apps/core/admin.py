from django.contrib import admin

from .models import Filial, Membro, Organizacao, Setor


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "criado_em")
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ("nome", "organizacao")
    list_filter = ("organizacao",)
    search_fields = ("nome",)


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "filial", "organizacao")
    list_filter = ("organizacao", "filial")
    search_fields = ("nome",)


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ("usuario", "organizacao", "papel", "ativo")
    list_filter = ("organizacao", "papel", "ativo")
    search_fields = ("usuario__username", "usuario__email")
