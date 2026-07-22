"""Testes funcionais (Django test client) da tela de Pessoas.

Mesmo padrao das telas de Premissas e Frota: `Client(enforce_csrf_checks=True)`
cobre o cenario de CSRF ausente, e a regressao do numero com virgula
(LANGUAGE_CODE=pt-br quebrando <input type="number">) tambem e coberta.

Custo Mensal/HH sao calculados pelo motor (apps/motor/horas.py) usando o
calendario vigente (apps/premissas/services.py) — os testes verificam o
resultado numerico batendo com a formula normativa (SPEC_Funcional.md SS3.1).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client

from apps.cadastro.models import Oficina, Pessoa
from apps.core.models import Organizacao
from apps.premissas.models import ConjuntoPremissas

pytestmark = pytest.mark.django_db


@pytest.fixture
def org() -> Organizacao:
    return Organizacao.objects.create(nome="Fazenda Teste", slug="fazenda-teste")


@pytest.fixture
def oficina(org) -> Oficina:
    return Oficina.objects.create(
        organizacao=org,
        nome="Mec. Oficina",
        prev_pct=60,
        corr_pct=40,
        deflator_pct=5,
        terceiros_pct=10,
        disp_mo={
            "h_brutas": 8.8,
            "almoco": 1.2,
            "cafe": 0.17,
            "prod": 80,
            "abs": 5,
            "ferias": 8.33,
            "trein": 16,
            "abr_os": 0.25,
        },
    )


@pytest.fixture
def pessoa(org, oficina) -> Pessoa:
    return Pessoa.objects.create(
        organizacao=org,
        nome="João Mecânico",
        oficina=oficina,
        cargo="Mecânico",
        turno="Diurno",
        salario=Decimal("3000"),
        encargos_pct=Decimal("80"),
    )


def test_index_lista_pessoas_da_organizacao(client, org, pessoa):
    resposta = client.get(f"/{org.slug}/pessoas/")
    assert resposta.status_code == 200
    assert "João Mecânico" in resposta.content.decode()


def test_index_nao_mostra_pessoas_de_outra_organizacao(client, org, oficina):
    outra_org = Organizacao.objects.create(nome="Outra Fazenda", slug="outra-fazenda")
    outra_oficina = Oficina.objects.create(
        organizacao=outra_org, nome="Oficina X", prev_pct=50, corr_pct=50, deflator_pct=0
    )
    Pessoa.objects.create(
        organizacao=outra_org,
        nome="Pessoa De Outra Org",
        oficina=outra_oficina,
        cargo="Mecânico",
        turno="Diurno",
        salario=Decimal("1000"),
        encargos_pct=Decimal("80"),
    )
    resposta = client.get(f"/{org.slug}/pessoas/")
    assert "Pessoa De Outra Org" not in resposta.content.decode()


def test_index_usa_calendario_padrao_quando_nao_ha_conjunto_de_premissas(client, org, pessoa):
    """Sem ConjuntoPremissas ainda criado, a tela deve usar o calendario
    padrao (22 dias uteis/mes) em vez de quebrar."""
    assert not ConjuntoPremissas.objects.for_org(org).exists()
    resposta = client.get(f"/{org.slug}/pessoas/")
    assert resposta.status_code == 200


def test_index_calcula_custo_mensal_e_custo_hora(client, org, pessoa):
    # custo_mensal = 3000 * (1+80/100) = 5400 (SPEC_Funcional.md SS3.1, formula 8)
    resposta = client.get(f"/{org.slug}/pessoas/").content.decode()
    assert "R$ 5400" in resposta


def test_atualizar_numero_salario_persiste_no_banco(client, org, pessoa):
    resposta = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/numero/",
        {"campo": "salario", "valor": "3500"},
    )
    assert resposta.status_code == 200
    pessoa.refresh_from_db()
    assert pessoa.salario == Decimal("3500")


def test_atualizar_numero_campo_invalido_retorna_400(client, org, pessoa):
    resposta = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/numero/",
        {"campo": "nome", "valor": "1"},
    )
    assert resposta.status_code == 400


def test_atualizar_select_turno(client, org, pessoa):
    resposta = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/select/",
        {"campo": "turno", "valor": "Noturno"},
    )
    assert resposta.status_code == 200
    pessoa.refresh_from_db()
    assert pessoa.turno == "Noturno"


def test_atualizar_select_status_invalido_retorna_400(client, org, pessoa):
    resposta = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/select/",
        {"campo": "status", "valor": "Nao Existe"},
    )
    assert resposta.status_code == 400


def test_atualizar_oficina(client, org, pessoa):
    nova_oficina = Oficina.objects.create(
        organizacao=org, nome="Oficina Nova", prev_pct=50, corr_pct=50, deflator_pct=0
    )
    resposta = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/oficina/",
        {"oficina_id": nova_oficina.pk},
    )
    assert resposta.status_code == 200
    pessoa.refresh_from_db()
    assert pessoa.oficina_id == nova_oficina.pk


def test_post_sem_csrf_token_e_rejeitado(org, pessoa):
    csrf_client = Client(enforce_csrf_checks=True)
    resposta = csrf_client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/numero/",
        {"campo": "salario", "valor": "10"},
    )
    assert resposta.status_code == 403


def test_valor_no_input_usa_ponto_nao_virgula_decimal(client, org, pessoa):
    """`encargos_pct` tem decimal_places=2 no model: o valor volta do banco
    ja escalado (12.5 -> 12.50) — o que importa aqui e o separador (ponto,
    nao virgula), nao a quantidade de casas decimais."""
    resposta_post = client.post(
        f"/{org.slug}/pessoas/{pessoa.pk}/numero/",
        {"campo": "encargos_pct", "valor": "12.5"},
    ).content.decode()
    assert 'value="12.5"' in resposta_post
    assert "12,5" not in resposta_post

    resposta_get = client.get(f"/{org.slug}/pessoas/").content.decode()
    assert 'value="12.50"' in resposta_get
    assert "12,50" not in resposta_get
