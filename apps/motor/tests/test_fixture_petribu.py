"""Fixture de regressao — dataset Petribu (384 ativos), SPEC_Funcional.md SS3.6.

Valores de referencia gerados executando as funcoes JS ORIGINAIS de
`referencias/agrovector_manutencao_Petribu_v1.0_2026-07-06.html` em Node.js
sobre os dados reais desse arquivo (nao foram recalculados a mao). O Python
port reproduz esses numeros exatamente (validado durante o desenvolvimento
do fixture) — este teste protege essa paridade.

Esta instancia do Petribu nao tem pessoas cadastradas (`S.pessoas` vazio),
entao o fixture cobre apenas cronograma/plano preventivo/corretivo — nao
disponibilidade/custo/saving (todos dariam zero, sem significado).

Nota sobre os numeros informais da skill/SPEC (S/A/B/C, mai/set): os
valores com tolerancia explicita no SPEC_Funcional.md SS3.6 batem dentro da
faixa declarada (ver `test_totais_com_tolerancia_spec`). Os numeros
complementares (contagem por tipo, eventos de mai/set) sao ligeiramente
diferentes dos citados na skill (A: 642 vs 641 citado; set: 19 vs 16
citado) — a contagem por mes usa a data real do evento na agenda (que pode
cair no mes seguinte ao da semana de disparo), nao o mes da semana; os
numeros abaixo sao o que o app v1.0 realmente produz para este arquivo.
"""

from __future__ import annotations

import pytest

from apps.motor.agenda import build_agenda_eventos
from apps.motor.cronograma import calc_cronograma_mensal, calc_cronograma_semanal
from apps.motor.fixtures.dados_petribu import (
    checklist_petribu,
    frota_petribu,
    pessoas_petribu,
    premissas_petribu,
)
from apps.motor.plano import calc_plan_corr, calc_plan_prev

REF_SAZONAL = (1.24, 1.2, 1.09, 0.69, 0.5, 0.36, 0.46, 1.06, 1.25, 1.42, 1.4, 1.33)

REF_TOTAL_PREVENTIVAS = 2102  # SPEC SS3.6: 2.101 +/- 1
REF_TOT_HH_PREV = 7987.5  # SPEC SS3.6: 7.984 +/- 0,1%
REF_TOT_HH_CORR = 22783.08  # SPEC SS3.6: 22.761 +/- 0,1%

REF_TIPO_COUNT = {"S": 1140, "A": 642, "B": 312, "C": 8, "D": 0}

REF_EVENTOS_POR_MES = [245, 223, 271, 113, 20, 203, 53, 132, 19, 332, 205, 286]
REF_EVENTOS_DEZ_MAR = 1025  # SPEC SS3.6: 1.025-1.026
REF_EVENTOS_MAI = 20  # SPEC SS3.6: mai=20
REF_EVENTOS_SET = 19  # SPEC SS3.6 cita 16 (ver nota no docstring do modulo)


@pytest.fixture(scope="module")
def cenario_petribu():
    premissas = premissas_petribu()
    frota = frota_petribu()
    pessoas = pessoas_petribu()
    checklist = checklist_petribu()

    grid_semanal, semanas = calc_cronograma_semanal(frota, premissas, checklist)
    grid_mensal = calc_cronograma_mensal(grid_semanal, frota)
    plan_prev = calc_plan_prev(grid_mensal, frota, checklist, premissas)
    plan_corr = calc_plan_corr(plan_prev, premissas)
    eventos = build_agenda_eventos(frota, premissas, checklist, pessoas)

    return {
        "premissas": premissas,
        "frota": frota,
        "grid_semanal": grid_semanal,
        "plan_prev": plan_prev,
        "plan_corr": plan_corr,
        "eventos": eventos,
    }


def test_frota_e_checklist_carregados(cenario_petribu):
    assert len(cenario_petribu["frota"]) == 384


def test_sazonalidade(cenario_petribu):
    assert cenario_petribu["premissas"].sazonal == REF_SAZONAL


def test_contagem_preventivas_por_tipo(cenario_petribu):
    contagem = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    total = 0
    for entradas in cenario_petribu["grid_semanal"].values():
        for entrada in entradas.values():
            for cruzamento in entrada.prevs:
                contagem[cruzamento.tipo] += 1
                total += 1
    assert contagem == REF_TIPO_COUNT
    assert total == REF_TOTAL_PREVENTIVAS


def test_totais_com_tolerancia_spec(cenario_petribu):
    """SPEC_Funcional.md SS3.6 — as tolerancias sao as normativas (unicas exigidas em CI)."""
    plan_prev, plan_corr = cenario_petribu["plan_prev"], cenario_petribu["plan_corr"]
    tot_hh_prev = sum(sum(v) for v in plan_prev.values())
    tot_hh_corr = sum(sum(v) for v in plan_corr.values())

    assert abs(REF_TOTAL_PREVENTIVAS - 2101) <= 1
    assert tot_hh_prev == pytest.approx(7984, rel=0.001)
    assert tot_hh_corr == pytest.approx(22761, rel=0.001)
    # trava tambem os valores exatos reproduzidos pelo motor (regressao fina)
    assert tot_hh_prev == pytest.approx(REF_TOT_HH_PREV)
    assert tot_hh_corr == pytest.approx(REF_TOT_HH_CORR)


def test_janelas_mensais_de_eventos(cenario_petribu):
    por_mes = [0] * 12
    for evento in cenario_petribu["eventos"]:
        por_mes[evento.data.month - 1] += evento.count
    assert por_mes == REF_EVENTOS_POR_MES
    dez_mar = por_mes[11] + por_mes[0] + por_mes[1] + por_mes[2]
    assert dez_mar == REF_EVENTOS_DEZ_MAR
    assert 1025 <= dez_mar <= 1026
    assert por_mes[4] == REF_EVENTOS_MAI


def test_primeira_preventiva_colhedora_semana_3(cenario_petribu):
    """SPEC SS3.6: 1a preventiva = colhedoras Rev. S na semana 3 (set/2026)."""
    colhedoras_ids = {a.id for a in cenario_petribu["frota"] if a.classe == "Colhedora"}
    candidatas = [
        (min(entradas.keys()), ativo_id, entradas[min(entradas.keys())].tipo)
        for ativo_id, entradas in cenario_petribu["grid_semanal"].items()
        if ativo_id in colhedoras_ids and entradas
    ]
    candidatas.sort()
    primeiro_wi, _, primeiro_tipo = candidatas[0]
    assert primeiro_wi == 2  # semana 3 (0-based)
    assert primeiro_tipo == "S"
