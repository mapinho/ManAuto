"""Planos preventivo, corretivo e disponibilidade — SPEC_Funcional.md SS3.3-3.4 e modulos 7-9."""

from __future__ import annotations

from .arredondamento import r2
from .heranca import get_itens_checklist
from .horas import calc_horas_liquidas
from .tipos import Ativo, EntradaMensal, ItemChecklist, Pessoa, Premissas


def calc_plan_prev(
    cron_mensal: dict[int, dict[int, EntradaMensal]],
    frota: list[Ativo],
    checklist: list[ItemChecklist],
    premissas: Premissas,
) -> dict[str, list[float]]:
    res: dict[str, list[float]] = {of: [0.0] * 12 for of in premissas.oficinas}
    for ativo in frota:
        if ativo.status != "Ativo":
            continue
        ac = cron_mensal.get(ativo.id, {})
        for m, entrada in ac.items():
            for p in entrada.prevs:
                for item in get_itens_checklist(ativo.classe, p.tipo, checklist, premissas.heranca):
                    if item.oficina in res:
                        res[item.oficina][m] = r2(res[item.oficina][m] + item.hh)
    return res


def _js_or(valor: float | None, padrao: float) -> float:
    """Replica o operador `||` do JS: qualquer valor falsy (incl. 0) vira `padrao`.

    Porta fiel de um comportamento do prototipo original (`idx.corr||50`,
    `idx.prev||50`): um indice configurado como 0 (ex.: "corr: 0" para
    representar "sem corretiva esperada") acaba substituido por 50. E uma
    inconsistencia do app v4.2, mas alterar a formula exige aprovacao do
    Fabio (CLAUDE.md) — replicada aqui para manter paridade com os
    fixtures de regressao.
    """
    return valor if valor else padrao


def calc_plan_corr(
    plan_prev: dict[str, list[float]],
    premissas: Premissas,
    ignorar_deflator: bool = False,
) -> dict[str, list[float]]:
    res: dict[str, list[float]] = {of: [0.0] * 12 for of in premissas.oficinas}
    for of in premissas.oficinas:
        idx = premissas.indices.get(of)
        prev = max(0.01, _js_or(idx.prev if idx else None, 50.0))
        corr = _js_or(idx.corr if idx else None, 50.0)
        deflator = 0.0 if ignorar_deflator else _js_or(idx.deflator if idx else None, 0.0)
        ratio = corr / prev
        for m in range(12):
            base = plan_prev[of][m] * ratio
            defl_fator = 1 - (deflator / 100) * (m / 11 + 0.5) * 0.5
            saz = premissas.sazonal[m] if premissas.sazonal else 1.0
            res[of][m] = r2(max(0.0, base * defl_fator * saz))
    return res


def calc_disp_mes(premissas: Premissas, pessoas: list[Pessoa]) -> dict[str, list[float]]:
    res: dict[str, list[float]] = {of: [0.0] * 12 for of in premissas.oficinas}
    for of in premissas.oficinas:
        n = sum(1 for p in pessoas if p.oficina == of and p.status == "Ativo")
        disp_of = premissas.disp.get(of)
        liquidas = calc_horas_liquidas(disp_of).liquidas if disp_of else 0.0
        for m in range(12):
            res[of][m] = r2(n * premissas.dias_uteis[m] * liquidas)
    return res
