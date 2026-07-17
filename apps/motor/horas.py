"""Horas liquidas e custo de mao de obra — SPEC_Funcional.md SS3.1."""

from __future__ import annotations

from .arredondamento import r2
from .tipos import CustoPessoa, DispOficina, HorasLiquidas, Pessoa


def calc_horas_liquidas(disp: DispOficina) -> HorasLiquidas:
    efetivas = max(0.0, disp.h_brutas - disp.almoco - disp.cafe - disp.abr_os)
    fa = (disp.abs_ / 100) + (disp.ferias / 100 / 12) + (disp.trein / max(1.0, 252 * efetivas))
    liquidas = efetivas * (1 - min(fa, 0.99)) * (disp.prod / 100)
    return HorasLiquidas(efetivas=r2(efetivas), liquidas=r2(liquidas))


def calc_custo_pessoa(
    pessoa: Pessoa, disp_oficina: DispOficina, dias_uteis: tuple[float, ...]
) -> CustoPessoa:
    dias_medios = sum(dias_uteis) / 12
    liquidas = calc_horas_liquidas(disp_oficina).liquidas
    custo_mensal = pessoa.salario * (1 + pessoa.encargos / 100)
    horas_mes = dias_medios * liquidas
    custo_hora = custo_mensal / horas_mes if horas_mes > 0 else 0.0
    return CustoPessoa(custo_mensal=r2(custo_mensal), custo_hora=r2(custo_hora))


def custo_hh_oficina(
    oficina: str,
    pessoas: list[Pessoa],
    disp_por_oficina: dict[str, DispOficina],
    dias_uteis: tuple[float, ...],
) -> float:
    ativas = [p for p in pessoas if p.oficina == oficina and p.status == "Ativo"]
    if not ativas:
        return 0.0
    disp_oficina = disp_por_oficina[oficina]
    soma = sum(calc_custo_pessoa(p, disp_oficina, dias_uteis).custo_hora for p in ativas)
    return r2(soma / len(ativas))
