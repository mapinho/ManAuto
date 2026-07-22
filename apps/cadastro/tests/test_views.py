"""Testes funcionais (Django test client) da tela de Frota.

Mesmo padrao da tela de Premissas (apps/premissas/tests/test_views.py):
o `Client` padrao nao valida CSRF, entao os POSTs HTMX usam
`Client(enforce_csrf_checks=True)` quando o teste precisa cobrir esse
cenario. A regressao do numero com virgula (LANGUAGE_CODE=pt-br quebrando
<input type="number">) tambem e coberta aqui, pois a tela repete o mesmo
padrao de campo editavel da tela de Premissas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client

from apps.cadastro.models import Ativo, ClasseAtivo, Oficina
from apps.core.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def org() -> Organizacao:
    return Organizacao.objects.create(nome="Fazenda Teste", slug="fazenda-teste")


@pytest.fixture
def classe(org) -> ClasseAtivo:
    return ClasseAtivo.objects.create(organizacao=org, nome="Trator", unidade="Horas")


@pytest.fixture
def oficina(org) -> Oficina:
    return Oficina.objects.create(
        organizacao=org,
        nome="Mec. Oficina",
        prev_pct=60,
        corr_pct=40,
        deflator_pct=5,
        terceiros_pct=10,
    )


@pytest.fixture
def ativo(org, classe, oficina) -> Ativo:
    return Ativo.objects.create(
        organizacao=org,
        nome="Trator 001",
        classe=classe,
        oficina=oficina,
        tipo_gatilho="Horas",
        uso_atual=Decimal("120"),
        uso_sem_safra=Decimal("200"),
        uso_sem_entressafra=Decimal("100"),
        intervalo=Decimal("250"),
    )


def test_index_lista_ativos_da_organizacao(client, org, ativo):
    resposta = client.get(f"/{org.slug}/frota/")
    assert resposta.status_code == 200
    assert "Trator 001" in resposta.content.decode()


def test_index_nao_mostra_ativos_de_outra_organizacao(client, org, classe, oficina):
    outra_org = Organizacao.objects.create(nome="Outra Fazenda", slug="outra-fazenda")
    outra_classe = ClasseAtivo.objects.create(organizacao=outra_org, nome="Trator", unidade="Horas")
    Ativo.objects.create(
        organizacao=outra_org,
        nome="Ativo De Outra Org",
        classe=outra_classe,
        tipo_gatilho="Horas",
        intervalo=Decimal("250"),
    )
    resposta = client.get(f"/{org.slug}/frota/")
    assert "Ativo De Outra Org" not in resposta.content.decode()


def test_index_calcula_proxima_preventiva(client, org, ativo):
    """uso=120, itv=250 -> restante=130; uso_medio=(200+100)/2=150 -> meses=0.9,
    que cai no rotulo "< 1 mês" (mesma regra do prototipo v4.2: meses<1).
    A quantidade restante (130), essa sim exibida, e celula so-leitura (nao e
    <input>): formato brasileiro (virgula) e o esperado ali (vector-relatorios).
    """
    resposta = client.get(f"/{org.slug}/frota/").content.decode()
    assert "&lt; 1 mês" in resposta
    assert "130" in resposta


def test_index_exibe_meses_em_formato_brasileiro_quando_maior_que_um(client, org, classe):
    # itv=250, uso=0 -> restante=250; uso_medio=(50+50)/2=50 -> meses=5.0
    Ativo.objects.create(
        organizacao=org,
        nome="Trator Em Dia",
        classe=classe,
        tipo_gatilho="Horas",
        uso_atual=Decimal("0"),
        uso_sem_safra=Decimal("50"),
        uso_sem_entressafra=Decimal("50"),
        intervalo=Decimal("250"),
    )
    resposta = client.get(f"/{org.slug}/frota/").content.decode()
    assert "5,0 meses" in resposta


def test_filtro_por_classe(client, org, classe, oficina):
    outra_classe = ClasseAtivo.objects.create(organizacao=org, nome="Colhedora", unidade="Horas")
    Ativo.objects.create(
        organizacao=org,
        nome="Colhedora 001",
        classe=outra_classe,
        tipo_gatilho="Horas",
        intervalo=Decimal("250"),
    )
    resposta = client.get(f"/{org.slug}/frota/", {"classe": classe.pk}).content.decode()
    assert "Colhedora 001" not in resposta


def test_atualizar_numero_persiste_no_banco(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/numero/",
        {"campo": "uso_atual", "valor": "180"},
    )
    assert resposta.status_code == 200
    ativo.refresh_from_db()
    assert ativo.uso_atual == Decimal("180")


def test_atualizar_numero_campo_invalido_retorna_400(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/numero/",
        {"campo": "nome", "valor": "1"},
    )
    assert resposta.status_code == 400


def test_atualizar_select_status(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/select/",
        {"campo": "status", "valor": "Reforma"},
    )
    assert resposta.status_code == 200
    ativo.refresh_from_db()
    assert ativo.status == "Reforma"


def test_atualizar_select_valor_invalido_retorna_400(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/select/",
        {"campo": "status", "valor": "Nao Existe"},
    )
    assert resposta.status_code == 400


def test_atualizar_classe(client, org, ativo):
    nova_classe = ClasseAtivo.objects.create(organizacao=org, nome="Colhedora", unidade="Horas")
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/classe/",
        {"classe_id": nova_classe.pk},
    )
    assert resposta.status_code == 200
    ativo.refresh_from_db()
    assert ativo.classe_id == nova_classe.pk


def test_atualizar_oficina_para_vazio_desvincula(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/oficina/",
        {"oficina_id": ""},
    )
    assert resposta.status_code == 200
    ativo.refresh_from_db()
    assert ativo.oficina_id is None


def test_atualizar_garantia(client, org, ativo):
    resposta = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/garantia/",
        {"valor": "true"},
    )
    assert resposta.status_code == 200
    ativo.refresh_from_db()
    assert ativo.garantia is True


def test_post_sem_csrf_token_e_rejeitado(org, ativo):
    csrf_client = Client(enforce_csrf_checks=True)
    resposta = csrf_client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/numero/",
        {"campo": "uso_atual", "valor": "10"},
    )
    assert resposta.status_code == 403


def test_valor_no_input_usa_ponto_nao_virgula_decimal(client, org, ativo):
    """Mesma regressao coberta em apps/premissas: HTML5 <input type="number">
    exige ponto decimal, mas LANGUAGE_CODE="pt-br" faz Django renderizar
    com virgula — o navegador rejeita o valor silenciosamente ao recarregar.
    """
    resposta_post = client.post(
        f"/{org.slug}/frota/ativo/{ativo.pk}/numero/",
        {"campo": "uso_sem_safra", "valor": "0.25"},
    ).content.decode()
    assert 'value="0.25"' in resposta_post
    assert "0,25" not in resposta_post

    resposta_get = client.get(f"/{org.slug}/frota/").content.decode()
    assert 'value="0.25"' in resposta_get
    assert "0,25" not in resposta_get
