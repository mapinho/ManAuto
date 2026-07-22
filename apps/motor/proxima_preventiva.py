"""Estimativa de proxima preventiva por uso corrente vs. intervalo (tela de Frota).

Replica `calcProxPrev` do prototipo v4.2. Nao e uma das formulas normativas
do plano semanal (SPEC_Funcional.md SS3) — e apenas um indicador de UI para
destacar ativos proximos do vencimento, calculado a partir do uso acumulado
e do intervalo de preventiva do ativo.
"""

from __future__ import annotations

from dataclasses import dataclass

from .arredondamento import r1


@dataclass(frozen=True)
class ProximaPreventiva:
    restante: float
    meses: float


def calcular_proxima_preventiva(
    uso: float, intervalo: float, uso_medio_mensal: float
) -> ProximaPreventiva:
    if intervalo <= 0:
        return ProximaPreventiva(restante=0.0, meses=99.0)
    restante = intervalo - (uso % intervalo)
    meses = r1(restante / uso_medio_mensal) if uso_medio_mensal > 0 else 99.0
    return ProximaPreventiva(restante=restante, meses=meses)
