"""Selecao de organizacao — landing simples sem autenticacao ainda.

RBAC/login (SPEC_Funcional.md SS1: allauth, papeis) fica para uma fase
futura; por ora a organizacao vem direto da URL (`/<slug>/...`), e esta
tela so lista as organizacoes existentes para o usuario escolher.
"""

from django.shortcuts import render

from .models import Organizacao


def selecionar_organizacao(request):
    organizacoes = Organizacao.objects.order_by("nome")
    return render(request, "core/selecionar_organizacao.html", {"organizacoes": organizacoes})
