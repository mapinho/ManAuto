from django.contrib import admin

from .models import ConjuntoPremissas


@admin.register(ConjuntoPremissas)
class ConjuntoPremissasAdmin(admin.ModelAdmin):
    list_display = ("organizacao", "versao", "vigente", "criado_em")
    list_filter = ("organizacao", "vigente")
    ordering = ("-versao",)
