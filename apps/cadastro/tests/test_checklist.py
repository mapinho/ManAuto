"""Testes funcionais (Django test client) da tela de Checklist.

Mesmo padrao das demais telas: `Client(enforce_csrf_checks=True)` cobre o
cenario de CSRF ausente, e a regressao do numero com virgula (LANGUAGE_CODE=
pt-br quebrando <input type="number">) tambem e coberta para o campo HH.

O agrupamento por checklist usa `nome_checklist` quando presente (dado real
do importador — apps/importacao/importadores/checklist.py) ou um rotulo
derivado de classe+tipo quando ausente (dados semeados por seed_demo, que
nao preenchem id_checklist/nome_checklist — ver apps/cadastro/seeding.py).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client

from apps.cadastro.models import (
    AtividadeMaterial,
    ChecklistAtividade,
    ClasseAtivo,
    ItemMaterial,
    Oficina,
)
from apps.core.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def org() -> Organizacao:
    return Organizacao.objects.create(nome="Fazenda Teste", slug="fazenda-teste")


@pytest.fixture
def oficina(org) -> Oficina:
    return Oficina.objects.create(
        organizacao=org, nome="Mec. Oficina", prev_pct=60, corr_pct=40, deflator_pct=5
    )


@pytest.fixture
def classe(org) -> ClasseAtivo:
    return ClasseAtivo.objects.create(organizacao=org, nome="Trator", unidade="Horas")


@pytest.fixture
def atividade(org, classe, oficina) -> ChecklistAtividade:
    return ChecklistAtividade.objects.create(
        organizacao=org,
        classe=classe,
        tipo_prev="S",
        oficina=oficina,
        nome_checklist="Rev. S — Trator",
        descricao="Troca de óleo",
        cargo="Mecânico",
        tipo_atividade="Troca",
        hh=Decimal("1.5"),
    )


def test_index_lista_atividades_da_organizacao(client, org, atividade):
    resposta = client.get(f"/{org.slug}/checklist/")
    assert resposta.status_code == 200
    assert "Troca de óleo" in resposta.content.decode()
    assert "Rev. S — Trator" in resposta.content.decode()


def test_index_nao_mostra_atividades_de_outra_organizacao(client, org, classe, oficina):
    outra_org = Organizacao.objects.create(nome="Outra Fazenda", slug="outra-fazenda")
    outra_classe = ClasseAtivo.objects.create(organizacao=outra_org, nome="Trator", unidade="Horas")
    outra_oficina = Oficina.objects.create(
        organizacao=outra_org, nome="Oficina X", prev_pct=50, corr_pct=50, deflator_pct=0
    )
    ChecklistAtividade.objects.create(
        organizacao=outra_org,
        classe=outra_classe,
        tipo_prev="S",
        oficina=outra_oficina,
        descricao="Atividade De Outra Org",
        cargo="Mecânico",
        tipo_atividade="Troca",
        hh=Decimal("1"),
    )
    resposta = client.get(f"/{org.slug}/checklist/")
    assert "Atividade De Outra Org" not in resposta.content.decode()


def test_agrupa_por_classe_tipo_quando_nome_checklist_ausente(client, org, classe, oficina):
    ChecklistAtividade.objects.create(
        organizacao=org,
        classe=classe,
        tipo_prev="A",
        oficina=oficina,
        descricao="Verificação de freios",
        cargo="Mecânico",
        tipo_atividade="Verificação",
        hh=Decimal("0.5"),
    )
    resposta = client.get(f"/{org.slug}/checklist/").content.decode()
    assert "Trator — Revisão A" in resposta


def test_exibe_resumo_de_insumos_e_pecas(client, org, atividade):
    insumo = ItemMaterial.objects.create(
        organizacao=org, descricao="Óleo 15W40", tipo=ItemMaterial.Tipo.INSUMO, unidade="L"
    )
    AtividadeMaterial.objects.create(
        organizacao=org, atividade=atividade, item=insumo, qtd=Decimal("5"), unidade="L"
    )
    resposta = client.get(f"/{org.slug}/checklist/").content.decode()
    assert "Óleo 15W40" in resposta


def test_filtro_por_tipo_prev(client, org, classe, oficina, atividade):
    ChecklistAtividade.objects.create(
        organizacao=org,
        classe=classe,
        tipo_prev="B",
        oficina=oficina,
        nome_checklist="Rev. B — Trator",
        descricao="Troca de filtro",
        cargo="Mecânico",
        tipo_atividade="Troca",
        hh=Decimal("2"),
    )
    resposta = client.get(f"/{org.slug}/checklist/", {"tipo_prev": "B"}).content.decode()
    assert "Troca de filtro" in resposta
    assert "Troca de óleo" not in resposta


def test_atualizar_numero_hh_persiste_no_banco(client, org, atividade):
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/numero/",
        {"campo": "hh", "valor": "2.5"},
    )
    assert resposta.status_code == 200
    atividade.refresh_from_db()
    assert atividade.hh == Decimal("2.5")


def test_atualizar_numero_campo_invalido_retorna_400(client, org, atividade):
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/numero/",
        {"campo": "id_externo", "valor": "1"},
    )
    assert resposta.status_code == 400


def test_atualizar_texto_descricao(client, org, atividade):
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/texto/",
        {"campo": "descricao", "valor": "Troca de óleo e filtro"},
    )
    assert resposta.status_code == 200
    atividade.refresh_from_db()
    assert atividade.descricao == "Troca de óleo e filtro"


def test_atualizar_texto_vazio_retorna_400(client, org, atividade):
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/texto/",
        {"campo": "descricao", "valor": "   "},
    )
    assert resposta.status_code == 400


def test_atualizar_texto_campo_invalido_retorna_400(client, org, atividade):
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/texto/",
        {"campo": "hh", "valor": "abc"},
    )
    assert resposta.status_code == 400


def test_atualizar_oficina(client, org, atividade):
    nova_oficina = Oficina.objects.create(
        organizacao=org, nome="Oficina Nova", prev_pct=50, corr_pct=50, deflator_pct=0
    )
    resposta = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/oficina/",
        {"oficina_id": nova_oficina.pk},
    )
    assert resposta.status_code == 200
    atividade.refresh_from_db()
    assert atividade.oficina_id == nova_oficina.pk


def test_post_sem_csrf_token_e_rejeitado(org, atividade):
    csrf_client = Client(enforce_csrf_checks=True)
    resposta = csrf_client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/numero/",
        {"campo": "hh", "valor": "1"},
    )
    assert resposta.status_code == 403


def test_valor_no_input_hh_usa_ponto_nao_virgula_decimal(client, org, atividade):
    """A celula so-leitura "Total HH" no topo da pagina legitimamente
    mostra virgula (formato brasileiro) — so o atributo `value` do <input>
    editavel precisa usar ponto (HTML5), por isso a checagem e restrita a
    esse atributo, nao ao HTML inteiro."""
    resposta_post = client.post(
        f"/{org.slug}/checklist/atividade/{atividade.pk}/numero/",
        {"campo": "hh", "valor": "0.25"},
    ).content.decode()
    assert 'value="0.25"' in resposta_post
    assert 'value="0,25"' not in resposta_post

    resposta_get = client.get(f"/{org.slug}/checklist/").content.decode()
    assert 'value="0.25"' in resposta_get
    assert 'value="0,25"' not in resposta_get
