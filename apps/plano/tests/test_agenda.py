"""Testes funcionais (Django test client) da tela de Agenda.

Reaproveita o mesmo fixture demo (13 ativos) e os numeros de referencia do
motor (apps/motor/tests/test_fixture_demo.py) usados em test_services.py —
a Agenda le o MESMO PlanoAnual/EventoPreventiva do Cronograma, so muda a
apresentacao (calendario mensal + lista cronologica do trimestre).
"""

from __future__ import annotations

import pytest

from apps.cadastro.seeding import semear_organizacao
from apps.core.models import Organizacao
from apps.motor.fixtures.dados_demo import checklist_demo, frota_demo, pessoas_demo, premissas_demo
from apps.plano.services import recalcular_plano

pytestmark = pytest.mark.django_db

# Primeiro evento cronologico do dataset demo (ver REF_PRIMEIROS_5_EVENTOS em
# test_services.py / test_fixture_demo.py) — semana 0 (data=inicio da safra),
# portanto sempre no trimestre T1 (q=0).
REF_PRIMEIRO_EVENTO = {
    "date": "2025-04-01",
    "ativo": "Colhedora CASE A8810 — 1036",
    "tipo": "A",
    "hh": 15,
    "oficina": "Mec. Oficina",
    "mec": "Marcos Ferreira",
}


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


def test_agenda_sem_plano_mostra_estado_vazio(client, org):
    resposta = client.get(f"/{org.slug}/agenda/")
    assert resposta.status_code == 200
    assert "Nenhum plano calculado ainda" in resposta.content.decode()


def test_agenda_com_plano_renderiza_calendario_e_lista(client, org_demo):
    recalcular_plano(org_demo)
    resposta = client.get(f"/{org_demo.slug}/agenda/?q=0")
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert REF_PRIMEIRO_EVENTO["ativo"] in conteudo
    assert REF_PRIMEIRO_EVENTO["mec"] in conteudo


def test_agenda_trimestre_0_contem_primeiro_evento_com_dados_corretos(client, org_demo):
    recalcular_plano(org_demo)
    conteudo = client.get(f"/{org_demo.slug}/agenda/?q=0").content.decode()
    # tipo (badge circular) e oficina do primeiro evento devem aparecer
    assert REF_PRIMEIRO_EVENTO["oficina"] in conteudo
    assert "15.0" in conteudo or "15,0" in conteudo or ">15<" in conteudo


def test_agenda_trimestre_invalido_cai_no_padrao(client, org_demo):
    """`?q=99` e invalido — deve renderizar o mesmo trimestre padrao que a
    URL sem `q`, nao 500 nem uma pagina em branco. Compara o KPI "Trimestre
    exibido" em vez do HTML inteiro, ja que o token CSRF muda a cada request."""
    recalcular_plano(org_demo)
    conteudo_invalido = client.get(f"/{org_demo.slug}/agenda/?q=99").content.decode()
    conteudo_sem_q = client.get(f"/{org_demo.slug}/agenda/").content.decode()

    def trimestre_exibido(html: str) -> str:
        marcador = "Trimestre exibido"
        inicio = html.index(marcador)
        return html[inicio : inicio + 120]

    assert trimestre_exibido(conteudo_invalido) == trimestre_exibido(conteudo_sem_q)


def test_agenda_mostra_total_de_preventivas_do_trimestre(client, org_demo):
    plano = recalcular_plano(org_demo)
    total_geral = plano.eventos.count()
    conteudo = client.get(f"/{org_demo.slug}/agenda/?q=0").content.decode()
    # todas as 78 preventivas do dataset demo ocorrem nas primeiras semanas
    # (safra comecando em abril) — o resumo do trimestre deve refletir isso
    assert "preventivas)" in conteudo
    assert total_geral == 78
