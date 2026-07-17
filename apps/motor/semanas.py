"""Calendario agricola — 52 semanas a partir do inicio da safra (SPEC_Funcional.md SS3.2)."""

from __future__ import annotations

from datetime import date, timedelta

from .tipos import Semana

_MESES_ABREV = (
    "jan.",
    "fev.",
    "mar.",
    "abr.",
    "mai.",
    "jun.",
    "jul.",
    "ago.",
    "set.",
    "out.",
    "nov.",
    "dez.",
)

N_SEMANAS = 52


def gerar_semanas(inicio_safra: date, fim_safra: date) -> list[Semana]:
    semanas = []
    d = inicio_safra
    for i in range(N_SEMANAS):
        fim = d + timedelta(days=6)
        safra = inicio_safra <= d <= fim_safra
        label = f"S{i + 1:02d} {d.day:02d} de {_MESES_ABREV[d.month - 1]}"
        semanas.append(Semana(idx=i, label=label, data=d, fim=fim, safra=safra, mes=d.month - 1))
        d = d + timedelta(days=7)
    return semanas
