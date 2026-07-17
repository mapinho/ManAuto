"""Helpers de cadastro compartilhados entre importadores (Frota, Pessoas, ...)."""

from __future__ import annotations

from apps.core.models import Filial, Organizacao, Setor


def obter_ou_criar_setor(organizacao: Organizacao, nome_filial: str, nome_centro: str) -> Setor:
    """Filial/Setor (= "centro de manutenção" nos templates Vector) nao carregam
    configuracao propria, entao sao criados automaticamente se ausentes —
    diferente de Oficina/ClasseAtivo, que exigem cadastro previo.
    """
    filial, _ = Filial.objects.for_org(organizacao).get_or_create(
        organizacao=organizacao, nome=nome_filial
    )
    setor, _ = Setor.objects.get_or_create(organizacao=organizacao, filial=filial, nome=nome_centro)
    return setor
