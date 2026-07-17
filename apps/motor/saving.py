"""Saving financeiro do plano preventivo — SPEC_Funcional.md SS3.5.

baseline[m] = HHprev[m] x ratio x sazonal[m]  (plano corretivo com deflator=0,
ou seja `calc_plan_corr(..., ignorar_deflator=True)`)
saving_R$[m] = (baseline[m] - HHcorr[m]) x custoHH_medio_oficina
"""

from __future__ import annotations

from dataclasses import dataclass

from .arredondamento import r2


@dataclass(frozen=True)
class ResultadoSaving:
    saving_mensal: dict[str, list[float]]  # por oficina, 12 meses
    saving_total_por_oficina: dict[str, float]
    saving_total_anual: float


def calc_saving(
    plan_corr_baseline: dict[str, list[float]],
    plan_corr: dict[str, list[float]],
    custo_hh_por_oficina: dict[str, float],
    oficinas: tuple[str, ...],
) -> ResultadoSaving:
    saving_mensal: dict[str, list[float]] = {}
    saving_total_por_oficina: dict[str, float] = {}

    for of in oficinas:
        chh = custo_hh_por_oficina.get(of, 0.0)
        mensal = [r2((plan_corr_baseline[of][m] - plan_corr[of][m]) * chh) for m in range(12)]
        saving_mensal[of] = mensal
        saving_total_por_oficina[of] = r2(sum(mensal))

    saving_total_anual = r2(sum(saving_total_por_oficina.values()))
    return ResultadoSaving(
        saving_mensal=saving_mensal,
        saving_total_por_oficina=saving_total_por_oficina,
        saving_total_anual=saving_total_anual,
    )
