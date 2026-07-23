"""Testes funcionais (Django test client) da tela de Cronograma.

GET sem plano calculado mostra o estado vazio; GET com plano calculado
(via `recalcular_plano` chamado diretamente no teste, nunca a task
Procrastinate) renderiza a grade. POST /recalcular so verifica que o
enfileiramento (`.defer()`) nao lanca excecao — processar de fato exige um
worker rodando (`manage.py procrastinate worker`), fora do escopo do teste.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.cadastro.seeding import semear_organizacao
from apps.core.models import Organizacao
from apps.motor.fixtures.dados_demo import checklist_demo, frota_demo, pessoas_demo, premissas_demo
from apps.plano.services import recalcular_plano

pytestmark = pytest.mark.django_db


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


def test_cronograma_sem_plano_mostra_estado_vazio(client, org):
    resposta = client.get(f"/{org.slug}/cronograma/")
    assert resposta.status_code == 200
    assert "Nenhum plano calculado ainda" in resposta.content.decode()


def test_cronograma_com_plano_renderiza_grade(client, org_demo):
    recalcular_plano(org_demo)
    resposta = client.get(f"/{org_demo.slug}/cronograma/")
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "Colhedora CASE A8810" in conteudo
    assert "421.25" in conteudo or "421,25" in conteudo or "421.2" in conteudo


def test_cronograma_mostra_kpis_corretos(client, org_demo):
    recalcular_plano(org_demo)
    conteudo = client.get(f"/{org_demo.slug}/cronograma/").content.decode()
    assert ">78<" in conteudo  # total_preventivas (REF_N_EVENTOS_AGENDA)


def test_recalcular_enfileira_sem_erro(client, org):
    resposta = client.post(f"/{org.slug}/cronograma/recalcular/")
    assert resposta.status_code == 200
    assert "Recalculo enfileirado" in resposta.content.decode()


def test_recalcular_sem_csrf_token_e_rejeitado(org):
    csrf_client = Client(enforce_csrf_checks=True)
    resposta = csrf_client.post(f"/{org.slug}/cronograma/recalcular/")
    assert resposta.status_code == 403
