"""Fixture de regressao — dataset demo (13 ativos, protótipo v4.2).

Valores de referencia gerados executando as funcoes JS ORIGINAIS do
`agrovector_manutencao_v4.2_2026-06-16.html` em Node.js sobre este mesmo
dataset (nao foram recalculados a mao) — ver skill agrovector-motor e
SPEC_Funcional.md SS3.6. Qualquer alteracao no motor que quebre estes
numeros exige o procedimento descrito na skill (aprovacao + novo fixture).
"""

from __future__ import annotations

import pytest

from apps.motor.agenda import build_agenda_eventos
from apps.motor.cronograma import calc_cronograma_mensal, calc_cronograma_semanal
from apps.motor.fixtures.dados_demo import checklist_demo, frota_demo, pessoas_demo, premissas_demo
from apps.motor.horas import calc_horas_liquidas, custo_hh_oficina
from apps.motor.plano import calc_disp_mes, calc_plan_corr, calc_plan_prev
from apps.motor.saving import calc_saving

REF_PLAN_PREV = {
    "Mec. Oficina": [0, 0.75, 24.25, 43.5, 20, 35.5, 40.5, 20.25, 28.75, 39.75, 28.25, 3],
    "Mec. Campo": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Elétrica": [0, 0, 5, 10, 4, 8, 10, 3, 5, 10, 6, 0],
    "Lubrificação": [0, 0.5, 3.25, 8.5, 5, 5.5, 8.5, 4.75, 5.25, 8, 6, 1],
    "Borracharia": [0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0],
    "Caldeiraria": [0, 1.5, 0, 0, 3, 0, 3, 0, 3, 1.5, 1.5, 0],
}

REF_PLAN_CORR = {
    "Mec. Oficina": [0, 0.74, 20.66, 34.13, 14.35, 23.1, 18.41, 7.87, 13.01, 23.06, 18.17, 2.7],
    "Mec. Campo": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Elétrica": [0, 0, 5.23, 9.63, 3.52, 6.39, 5.58, 1.43, 2.78, 7.12, 4.74, 0],
    "Lubrificação": [0, 0.38, 2.11, 5.1, 2.75, 2.75, 2.97, 1.43, 1.84, 3.6, 3, 0.7],
    "Borracharia": [0, 0, 2.98, 2.75, 0, 2.28, 0, 1.36, 1.58, 0, 2.25, 0],
    "Caldeiraria": [0, 8.92, 0, 0, 13.03, 0, 8.27, 0, 8.25, 5.29, 5.87, 0],
}

REF_PLAN_CORR_BASE = {
    "Mec. Oficina": [0, 0.75, 21.02, 34.8, 14.67, 23.67, 18.9, 8.1, 13.42, 23.85, 18.83, 2.8],
    "Mec. Campo": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Elétrica": [0, 0, 5.32, 9.82, 3.6, 6.55, 5.73, 1.47, 2.86, 7.36, 4.91, 0],
    "Lubrificação": [0, 0.38, 2.11, 5.1, 2.75, 2.75, 2.97, 1.43, 1.84, 3.6, 3, 0.7],
    "Borracharia": [0, 0, 3.03, 2.8, 0, 2.33, 0, 1.4, 1.63, 0, 2.33, 0],
    "Caldeiraria": [0, 9, 0, 0, 13.2, 0, 8.4, 0, 8.4, 5.4, 6, 0],
}

REF_DISP = {
    "Mec. Oficina": [
        472.56,
        429.6,
        472.56,
        429.6,
        429.6,
        472.56,
        451.08,
        429.6,
        494.04,
        472.56,
        451.08,
        494.04,
    ],
    "Mec. Campo": [
        234.08,
        212.8,
        234.08,
        212.8,
        212.8,
        234.08,
        223.44,
        212.8,
        244.72,
        234.08,
        223.44,
        244.72,
    ],
    "Elétrica": [
        236.28,
        214.8,
        236.28,
        214.8,
        214.8,
        236.28,
        225.54,
        214.8,
        247.02,
        236.28,
        225.54,
        247.02,
    ],
    "Lubrificação": [
        264.88,
        240.8,
        264.88,
        240.8,
        240.8,
        264.88,
        252.84,
        240.8,
        276.92,
        264.88,
        252.84,
        276.92,
    ],
    "Borracharia": [
        126.28,
        114.8,
        126.28,
        114.8,
        114.8,
        126.28,
        120.54,
        114.8,
        132.02,
        126.28,
        120.54,
        132.02,
    ],
    "Caldeiraria": [
        230.12,
        209.2,
        230.12,
        209.2,
        209.2,
        230.12,
        219.66,
        209.2,
        240.58,
        230.12,
        219.66,
        240.58,
    ],
}

REF_CUSTO_HH_OFICINA = {
    "Mec. Oficina": 71.31,
    "Mec. Campo": 57.59,
    "Elétrica": 69.07,
    "Lubrificação": 37.5,
    "Borracharia": 43.54,
    "Caldeiraria": 59.36,
}

REF_HORAS_LIQUIDAS = {
    "Mec. Oficina": (7.18, 5.37),
    "Mec. Campo": (7.66, 5.32),
    "Elétrica": (7.18, 5.37),
    "Lubrificação": (7.46, 6.02),
    "Borracharia": (7.46, 5.74),
    "Caldeiraria": (7.18, 5.23),
}

REF_TIPO_COUNT = {"S": 39, "A": 23, "B": 16, "C": 0, "D": 0}
REF_TOT_PREVENTIVAS = 78
REF_TOT_HH_PREV = 421.25
REF_TOT_HH_CORR = 312.08
REF_TOT_HH_DISP = 18201.6
REF_N_EVENTOS_AGENDA = 78

REF_PRIMEIROS_5_EVENTOS = [
    {
        "date": "2025-04-01",
        "ativo": "Colhedora CASE A8810 — 1036",
        "tipo": "A",
        "hh": 15,
        "oficina": "Mec. Oficina",
        "mec": "Marcos Ferreira",
    },
    {
        "date": "2025-04-02",
        "ativo": "Trator NH T7.315 — 401",
        "tipo": "S",
        "hh": 2,
        "oficina": "Mec. Oficina",
        "mec": "João Alves",
    },
    {
        "date": "2025-04-08",
        "ativo": "Colhedora CASE A9000 — 1043",
        "tipo": "S",
        "hh": 5.5,
        "oficina": "Mec. Oficina",
        "mec": "João Alves",
    },
    {
        "date": "2025-04-15",
        "ativo": "Toyota Hilux — 5002",
        "tipo": "S",
        "hh": 0,
        "oficina": "Mec. Oficina",
        "mec": "Carlos Rodrigues",
    },
    {
        "date": "2025-04-22",
        "ativo": "Colhedora JD CH570 — 1027",
        "tipo": "B",
        "hh": 15,
        "oficina": "Mec. Oficina",
        "mec": "Carlos Rodrigues",
    },
]


@pytest.fixture(scope="module")
def cenario_demo():
    premissas = premissas_demo()
    frota = frota_demo()
    pessoas = pessoas_demo()
    checklist = checklist_demo()

    grid_semanal, semanas = calc_cronograma_semanal(frota, premissas, checklist)
    grid_mensal = calc_cronograma_mensal(grid_semanal, frota)
    plan_prev = calc_plan_prev(grid_mensal, frota, checklist, premissas)
    plan_corr = calc_plan_corr(plan_prev, premissas)
    plan_corr_base = calc_plan_corr(plan_prev, premissas, ignorar_deflator=True)
    disp = calc_disp_mes(premissas, pessoas)
    eventos = build_agenda_eventos(frota, premissas, checklist, pessoas)
    custo_hh = {
        of: custo_hh_oficina(of, pessoas, premissas.disp, premissas.dias_uteis)
        for of in premissas.oficinas
    }
    saving = calc_saving(plan_corr_base, plan_corr, custo_hh, premissas.oficinas)

    return {
        "premissas": premissas,
        "pessoas": pessoas,
        "grid_semanal": grid_semanal,
        "semanas": semanas,
        "plan_prev": plan_prev,
        "plan_corr": plan_corr,
        "plan_corr_base": plan_corr_base,
        "disp": disp,
        "eventos": eventos,
        "custo_hh": custo_hh,
        "saving": saving,
    }


def test_plan_prev(cenario_demo):
    assert cenario_demo["plan_prev"] == pytest.approx(REF_PLAN_PREV)


def test_plan_corr(cenario_demo):
    assert cenario_demo["plan_corr"] == pytest.approx(REF_PLAN_CORR)


def test_plan_corr_baseline_sem_deflator(cenario_demo):
    assert cenario_demo["plan_corr_base"] == pytest.approx(REF_PLAN_CORR_BASE)


def test_disponibilidade_mensal(cenario_demo):
    assert cenario_demo["disp"] == pytest.approx(REF_DISP)


def test_totais_anuais(cenario_demo):
    plan_prev, plan_corr, disp = (
        cenario_demo["plan_prev"],
        cenario_demo["plan_corr"],
        cenario_demo["disp"],
    )
    tot_hh_prev = sum(sum(v) for v in plan_prev.values())
    tot_hh_corr = sum(sum(v) for v in plan_corr.values())
    tot_hh_disp = sum(sum(v) for v in disp.values())
    assert tot_hh_prev == pytest.approx(REF_TOT_HH_PREV)
    assert tot_hh_corr == pytest.approx(REF_TOT_HH_CORR)
    assert tot_hh_disp == pytest.approx(REF_TOT_HH_DISP)


def test_custo_hh_por_oficina(cenario_demo):
    premissas, pessoas = cenario_demo["premissas"], cenario_demo["pessoas"]
    for oficina, esperado in REF_CUSTO_HH_OFICINA.items():
        obtido = custo_hh_oficina(oficina, pessoas, premissas.disp, premissas.dias_uteis)
        assert obtido == pytest.approx(esperado), oficina


def test_horas_liquidas_por_oficina(cenario_demo):
    premissas = cenario_demo["premissas"]
    for oficina, (ef_esperado, liq_esperado) in REF_HORAS_LIQUIDAS.items():
        resultado = calc_horas_liquidas(premissas.disp[oficina])
        assert resultado.efetivas == pytest.approx(ef_esperado), oficina
        assert resultado.liquidas == pytest.approx(liq_esperado), oficina


def test_contagem_preventivas_por_tipo(cenario_demo):
    contagem = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    total = 0
    for entradas in cenario_demo["grid_semanal"].values():
        for entrada in entradas.values():
            for cruzamento in entrada.prevs:
                contagem[cruzamento.tipo] += 1
                total += 1
    assert contagem == REF_TIPO_COUNT
    assert total == REF_TOT_PREVENTIVAS


def test_primeira_preventiva_colhedora_a8810_1035(cenario_demo):
    """Regressao especifica: ativo id=1 tem 1a preventiva (tipo B) na semana 5, cu=6000."""
    entrada = cenario_demo["grid_semanal"][1][4]
    assert entrada.tipo == "B"
    assert entrada.hh == pytest.approx(15)
    assert entrada.prevs[0].cu == pytest.approx(6000)


def test_saving_anual(cenario_demo):
    """Saving anual segue SPEC_Funcional.md SS3.5 (granularidade mensal, somada por
    oficina). O app v4.2 exibe 471.26 na tela de Saving via uma soma anual que
    NAO arredonda os totais intermediarios por oficina antes de multiplicar pelo
    custo/HH; aqui a soma e feita mes a mes (cada mes arredondado), como manda a
    formula normativa — resulta em 471.27, dentro da tolerancia de 0,1% do SS3.6.
    """
    assert cenario_demo["saving"].saving_total_anual == pytest.approx(471.27)


def test_agenda_eventos(cenario_demo):
    eventos = cenario_demo["eventos"]
    assert len(eventos) == REF_N_EVENTOS_AGENDA
    for evento, esperado in zip(eventos[:5], REF_PRIMEIROS_5_EVENTOS, strict=True):
        assert evento.data.isoformat() == esperado["date"]
        assert evento.ativo == esperado["ativo"]
        assert evento.tipo == esperado["tipo"]
        assert evento.hh == pytest.approx(esperado["hh"])
        assert evento.oficina == esperado["oficina"]
        assert evento.mecanico == esperado["mec"]
