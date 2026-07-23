"""Regressao da persistencia do plano contra o fixture demo (13 ativos, ver
apps/motor/tests/test_fixture_demo.py) — os mesmos numeros de referencia
(gerados executando o JS original do prototipo v4.2 em Node.js) precisam
bater depois de passar pelo cadastro Django + `recalcular_plano`, nao so
dentro do motor puro. Isso prova que a conversao Django->motor->persistencia
(apps/cadastro/services.py, apps/premissas/services.py,
apps/plano/services.py) preserva os calculos.
"""

from __future__ import annotations

import pytest

from apps.cadastro.seeding import semear_organizacao
from apps.core.models import Organizacao
from apps.motor.fixtures.dados_demo import checklist_demo, frota_demo, pessoas_demo, premissas_demo
from apps.plano.models import EventoPreventiva, PlanoAnual
from apps.plano.services import plano_vigente, recalcular_plano

pytestmark = pytest.mark.django_db

REF_PLAN_PREV = {
    "Mec. Oficina": [0, 0.75, 24.25, 43.5, 20, 35.5, 40.5, 20.25, 28.75, 39.75, 28.25, 3],
    "Mec. Campo": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Elétrica": [0, 0, 5, 10, 4, 8, 10, 3, 5, 10, 6, 0],
    "Lubrificação": [0, 0.5, 3.25, 8.5, 5, 5.5, 8.5, 4.75, 5.25, 8, 6, 1],
    "Borracharia": [0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0],
    "Caldeiraria": [0, 1.5, 0, 0, 3, 0, 3, 0, 3, 1.5, 1.5, 0],
}
REF_TOT_HH_PREV = 421.25
REF_N_EVENTOS = 78
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


@pytest.fixture
def org():
    return Organizacao.objects.create(nome="Fazenda Vazia", slug="fazenda-vazia")


@pytest.fixture
def org_demo():
    return semear_organizacao(
        slug="demo-teste",
        nome="Demo Teste",
        premissas=premissas_demo(),
        frota=frota_demo(),
        pessoas=pessoas_demo(),
        checklist=checklist_demo(),
    )


def test_recalcular_plano_cria_planoanual(org_demo):
    plano = recalcular_plano(org_demo)
    assert isinstance(plano, PlanoAnual)
    assert plano.organizacao_id == org_demo.pk


def test_recalcular_plano_total_eventos_bate_com_fixture_do_motor(org_demo):
    plano = recalcular_plano(org_demo)
    assert plano.eventos.count() == REF_N_EVENTOS


def test_recalcular_plano_hh_prev_por_oficina_bate_com_fixture_do_motor(org_demo):
    plano = recalcular_plano(org_demo)
    for oficina, esperado in REF_PLAN_PREV.items():
        assert plano.hh_prev_por_oficina[oficina] == pytest.approx(esperado), oficina


def test_recalcular_plano_total_hh_anual_bate_com_fixture_do_motor(org_demo):
    plano = recalcular_plano(org_demo)
    total = sum(sum(v) for v in plano.hh_prev_por_oficina.values())
    assert total == pytest.approx(REF_TOT_HH_PREV)


def test_recalcular_plano_primeiros_eventos_com_fk_resolvidas(org_demo):
    plano = recalcular_plano(org_demo)
    eventos = list(
        plano.eventos.select_related("ativo", "oficina", "responsavel").order_by("data")[:5]
    )
    for evento, esperado in zip(eventos, REF_PRIMEIROS_5_EVENTOS, strict=True):
        assert evento.data.isoformat() == esperado["date"]
        assert evento.ativo.nome == esperado["ativo"]
        assert evento.tipo == esperado["tipo"]
        assert float(evento.hh) == pytest.approx(esperado["hh"])
        assert evento.oficina.nome == esperado["oficina"]
        assert evento.responsavel is not None
        assert evento.responsavel.nome == esperado["mec"]


def test_recalcular_plano_e_idempotente_em_execucoes_repetidas(org_demo):
    """Rodar duas vezes nao deve falhar (nem duplicar validacoes) — cada
    chamada cria um NOVO PlanoAnual, preservando o historico de calculos."""
    plano1 = recalcular_plano(org_demo)
    plano2 = recalcular_plano(org_demo)
    assert plano1.pk != plano2.pk
    assert PlanoAnual.objects.for_org(org_demo).count() == 2
    assert EventoPreventiva.objects.filter(plano_anual=plano1).count() == REF_N_EVENTOS
    assert EventoPreventiva.objects.filter(plano_anual=plano2).count() == REF_N_EVENTOS


def test_plano_vigente_retorna_o_mais_recente(org_demo):
    recalcular_plano(org_demo)
    mais_recente = recalcular_plano(org_demo)
    assert plano_vigente(org_demo).pk == mais_recente.pk


def test_plano_vigente_retorna_none_sem_plano_calculado(org):
    assert plano_vigente(org) is None
