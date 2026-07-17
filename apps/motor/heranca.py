"""Tipo de preventiva e heranca cumulativa de checklists — SPEC_Funcional.md SS3.2-3.3."""

from __future__ import annotations

from .arredondamento import r2, round_js
from .tipos import GatilhosClasse, ItemChecklist

HERANCA_PADRAO: dict[str, tuple[str, ...]] = {
    "S": ("S",),
    "A": ("S", "A"),
    "B": ("S", "A", "B"),
    "C": ("S", "A", "B", "C"),
    "D": ("S", "A", "B", "C", "D"),
}


def get_heranca(tipo: str, heranca: dict[str, tuple[str, ...]] | None = None) -> tuple[str, ...]:
    tabela = heranca or HERANCA_PADRAO
    return tabela.get(tipo, (tipo,))


def det_tipo(cum_uso: float, gatilhos: GatilhosClasse) -> str:
    itvs = sorted(
        (iv for iv in gatilhos.itvs if iv.valor > 0 and iv.tipo),
        key=lambda iv: iv.valor,
    )
    if not itvs:
        return "S"
    tipo = itvs[0].tipo
    for iv in itvs:
        if round_js(cum_uso) % round_js(iv.valor) == 0:
            tipo = iv.tipo
    return tipo


def calc_hh_checklist(
    classe: str,
    tipo_prev: str,
    checklist: list[ItemChecklist],
    heranca: dict[str, tuple[str, ...]] | None = None,
) -> float:
    tipos = get_heranca(tipo_prev, heranca)
    total = sum(c.hh for c in checklist if c.classe == classe and c.tipo_prev in tipos)
    return r2(total)


def get_itens_checklist(
    classe: str,
    tipo_prev: str,
    checklist: list[ItemChecklist],
    heranca: dict[str, tuple[str, ...]] | None = None,
) -> list[ItemChecklist]:
    tipos = get_heranca(tipo_prev, heranca)
    return [c for t in tipos for c in checklist if c.classe == classe and c.tipo_prev == t]
