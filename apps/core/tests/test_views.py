from __future__ import annotations

import pytest

from apps.core.models import Organizacao

pytestmark = pytest.mark.django_db


def test_selecionar_organizacao_lista_organizacoes(client):
    org = Organizacao.objects.create(nome="Fazenda Teste", slug="fazenda-teste")
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert org.nome in resposta.content.decode()


def test_selecionar_organizacao_vazia_mostra_aviso(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Nenhuma organiza" in resposta.content.decode()
