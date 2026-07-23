"""Task Procrastinate do recalculo de plano — nunca rodar no request (CLAUDE.md).

A tela de Cronograma (apps/plano/views.py) chama `.defer()` nesta task em
vez de rodar `recalcular_plano` sincronamente. Exige um worker rodando
(`manage.py procrastinate worker`) para efetivamente processar a fila —
em dev local sem Docker, isso significa um segundo terminal, ou usar
`manage.py recalcula_plano` (sincrono, mesmo padrao dos importadores).
"""

from __future__ import annotations

from procrastinate.contrib.django import app

from apps.core.models import Organizacao

from .services import recalcular_plano


@app.task(name="plano.recalcular")
def task_recalcular_plano(organizacao_id: int) -> int:
    organizacao = Organizacao.objects.get(pk=organizacao_id)
    plano = recalcular_plano(organizacao)
    return plano.pk
