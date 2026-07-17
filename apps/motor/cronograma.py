"""Cronograma de preventivas — disparo por gatilho e agregacao semanal/mensal.

SPEC_Funcional.md SS3.2: dispara preventiva quando o uso acumulado cruza um
multiplo do intervalo da classe; pode haver mais de um cruzamento por semana.
"""

from __future__ import annotations

import math

from .arredondamento import r2
from .heranca import calc_hh_checklist, det_tipo
from .semanas import gerar_semanas
from .tipos import (
    Ativo,
    Cruzamento,
    EntradaMensal,
    EntradaSemanal,
    ItemChecklist,
    Premissas,
    Semana,
)

_ORDEM_TIPOS = ("S", "A", "B", "C", "D")


def _tipo_predominante(prevs_ordenados: tuple[Cruzamento, ...]) -> str:
    """Tipo do primeiro item de `prevs_ordenados` (ja ordenado do maior para o menor tipo)."""
    return prevs_ordenados[0].tipo if prevs_ordenados else "S"


def calc_cronograma_semanal(
    frota: list[Ativo], premissas: Premissas, checklist: list[ItemChecklist]
) -> tuple[dict[int, dict[int, EntradaSemanal]], list[Semana]]:
    semanas = gerar_semanas(premissas.inicio_safra, premissas.fim_safra)
    grid: dict[int, dict[int, EntradaSemanal]] = {}

    for ativo in frota:
        if ativo.status != "Ativo":
            continue
        grid[ativo.id] = {}
        if not ativo.itv:
            continue
        gatilhos = premissas.gatilhos.get(ativo.classe)
        if gatilhos is None:
            continue

        uso_acum = ativo.uso
        for sem in semanas:
            uso_sem = ativo.uso_med_safra if sem.safra else ativo.uso_med_ent
            if not uso_sem:
                continue
            n_i = math.floor(uso_acum / ativo.itv)
            n_f = math.floor((uso_acum + uso_sem) / ativo.itv)
            if n_f > n_i:
                prevs = []
                for n in range(n_i + 1, n_f + 1):
                    cu = n * ativo.itv
                    tipo = det_tipo(cu, gatilhos)
                    hh = calc_hh_checklist(ativo.classe, tipo, checklist, premissas.heranca)
                    prevs.append(Cruzamento(tipo=tipo, hh=hh, cu=cu))
                prevs_ordenados = tuple(
                    sorted(prevs, key=lambda p: _ORDEM_TIPOS.index(p.tipo), reverse=True)
                )
                grid[ativo.id][sem.idx] = EntradaSemanal(
                    tipo=_tipo_predominante(prevs_ordenados),
                    hh=r2(sum(p.hh for p in prevs_ordenados)),
                    count=len(prevs_ordenados),
                    prevs=prevs_ordenados,
                    safra=sem.safra,
                    label=sem.label,
                    mes=sem.mes,
                )
            uso_acum = r2(uso_acum + uso_sem)

    return grid, semanas


def calc_cronograma_mensal(
    grid_semanal: dict[int, dict[int, EntradaSemanal]], frota: list[Ativo]
) -> dict[int, dict[int, EntradaMensal]]:
    grid: dict[int, dict[int, EntradaMensal]] = {}

    for ativo in frota:
        if ativo.status != "Ativo":
            continue
        grid[ativo.id] = {}
        ag = grid_semanal.get(ativo.id, {})
        for entrada in ag.values():
            m = entrada.mes
            atual = grid[ativo.id].get(m)
            if atual is None:
                grid[ativo.id][m] = EntradaMensal(
                    tipo=entrada.tipo, hh=entrada.hh, count=entrada.count, prevs=entrada.prevs
                )
            else:
                prevs = tuple(
                    sorted(
                        atual.prevs + entrada.prevs,
                        key=lambda p: _ORDEM_TIPOS.index(p.tipo),
                        reverse=True,
                    )
                )
                grid[ativo.id][m] = EntradaMensal(
                    tipo=_tipo_predominante(prevs),
                    hh=r2(atual.hh + entrada.hh),
                    count=atual.count + entrada.count,
                    prevs=prevs,
                )

    return grid
