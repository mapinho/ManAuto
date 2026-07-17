"""Tasks Procrastinate dos importadores — nunca rodar import pesado no request
(CLAUDE.md). Uma view de upload (tela HTMX, passo 5 do plano de migração)
deve chamar `.defer()` nestas tasks em vez de importar sincronamente.

O comando `manage.py importar` (apps/importacao/management/commands) roda os
mesmos importadores de forma síncrona — apropriado para uso via CLI/ops,
onde não há um request HTTP esperando resposta.
"""

from __future__ import annotations

from procrastinate.contrib.django import app

from apps.core.models import Organizacao

from .importadores.checklist import (
    importar_catalogo_itens,
    importar_checklist,
    importar_materiais_checklist,
)
from .importadores.frota import importar_frota
from .importadores.historico_os import importar_historico_os
from .importadores.pessoas import importar_pessoas
from .parsing import ResultadoImportacao


def _como_dict(resultado: ResultadoImportacao) -> dict:
    return {
        "total_linhas": resultado.total_linhas,
        "importados": resultado.importados,
        "erros": [{"linha": e.linha, "mensagem": e.mensagem} for e in resultado.erros],
    }


@app.task(name="importacao.frota")
def task_importar_frota(organizacao_id: int, caminho: str, origem_arquivo: str = "") -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(importar_frota(organizacao, caminho, origem_arquivo=origem_arquivo))


@app.task(name="importacao.pessoas")
def task_importar_pessoas(organizacao_id: int, caminho: str, origem_arquivo: str = "") -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(importar_pessoas(organizacao, caminho, origem_arquivo=origem_arquivo))


@app.task(name="importacao.catalogo_itens")
def task_importar_catalogo_itens(
    organizacao_id: int, caminho: str, origem_arquivo: str = ""
) -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(importar_catalogo_itens(organizacao, caminho, origem_arquivo=origem_arquivo))


@app.task(name="importacao.checklist")
def task_importar_checklist(organizacao_id: int, caminho: str, origem_arquivo: str = "") -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(importar_checklist(organizacao, caminho, origem_arquivo=origem_arquivo))


@app.task(name="importacao.materiais_checklist")
def task_importar_materiais_checklist(
    organizacao_id: int, caminho: str, origem_arquivo: str = ""
) -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(
        importar_materiais_checklist(organizacao, caminho, origem_arquivo=origem_arquivo)
    )


@app.task(name="importacao.historico_os")
def task_importar_historico_os(organizacao_id: int, caminho: str, origem_arquivo: str = "") -> dict:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    return _como_dict(importar_historico_os(organizacao, caminho, origem_arquivo=origem_arquivo))
