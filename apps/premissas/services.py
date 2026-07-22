"""Calendario vigente e horas liquidas por oficina — compartilhado entre telas.

Extraido de apps/premissas/views.py quando a tela de Pessoas passou a
precisar do mesmo calendario/disp_mo vigente para calcular custo/HH
(SPEC_Funcional.md SS3.1, formula 8) — Cronograma/Agenda/Disponibilidade
(proximas telas do roadmap) tambem vao depender disto. A view nunca
reimplementa a formula: quem calcula e sempre o motor (apps/motor/).
"""

from __future__ import annotations

from apps.cadastro.models import Oficina
from apps.core.models import Organizacao
from apps.motor.heranca import HERANCA_PADRAO
from apps.motor.horas import calc_horas_liquidas
from apps.motor.tipos import DispOficina, HorasLiquidas

from .models import ConjuntoPremissas

DISP_PADRAO = {
    "h_brutas": 8.8,
    "almoco": 1.0,
    "cafe": 0.17,
    "prod": 80,
    "abs": 5,
    "ferias": 8.33,
    "trein": 8,
    "abr_os": 0.17,
}

CALENDARIO_PADRAO = {
    "dias_uteis": [22] * 12,
    "safra": [False] * 12,
    "sazonal": [1.0] * 12,
    "inicio_safra": "2026-04-01",
    "fim_safra": "2026-11-30",
    "heranca": {tipo: list(itens) for tipo, itens in HERANCA_PADRAO.items()},
}


def conjunto_vigente(org: Organizacao, *, travar: bool = False) -> ConjuntoPremissas:
    """`travar=True` bloqueia a linha (SELECT ... FOR UPDATE) — exige rodar dentro
    de `transaction.atomic()`. Necessario em toda leitura-e-gravacao do JSON
    `calendario`: sem lock, dois POSTs quase simultaneos leem o mesmo JSON antes
    de qualquer um salvar, e o segundo `save()` sobrescreve a mudanca do
    primeiro (visto na pratica, ver historico do PR da tela de Premissas).
    """
    qs = ConjuntoPremissas.objects.for_org(org).filter(vigente=True).order_by("-versao")
    if travar:
        qs = qs.select_for_update()
    conjunto = qs.first()
    if conjunto is None:
        proxima_versao = (
            ConjuntoPremissas.objects.for_org(org)
            .order_by("-versao")
            .values_list("versao", flat=True)
            .first()
            or 0
        ) + 1
        conjunto = ConjuntoPremissas.objects.create(
            organizacao=org,
            versao=proxima_versao,
            vigente=True,
            calendario=dict(CALENDARIO_PADRAO),
        )
    return conjunto


def calendario(conjunto: ConjuntoPremissas) -> dict:
    return {**CALENDARIO_PADRAO, **conjunto.calendario}


def disp_oficina(oficina: Oficina) -> DispOficina:
    dados = {**DISP_PADRAO, **oficina.disp_mo}
    return DispOficina(
        h_brutas=float(dados["h_brutas"]),
        almoco=float(dados["almoco"]),
        cafe=float(dados["cafe"]),
        prod=float(dados["prod"]),
        abs_=float(dados["abs"]),
        ferias=float(dados["ferias"]),
        trein=float(dados["trein"]),
        abr_os=float(dados["abr_os"]),
    )


def horas_liquidas(oficina: Oficina) -> HorasLiquidas:
    """Chama o motor (apps/motor/horas.py) — nunca reimplementa a formula aqui."""
    return calc_horas_liquidas(disp_oficina(oficina))


__all__ = [
    "DISP_PADRAO",
    "CALENDARIO_PADRAO",
    "conjunto_vigente",
    "calendario",
    "disp_oficina",
    "horas_liquidas",
]
