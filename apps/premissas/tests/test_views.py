"""Testes funcionais (Django test client) da tela de Premissas.

Nao ha navegador aqui para conferir visualmente — estes testes garantem
que as views funcionam (status, persistencia no banco, HTMX), mas a
verificacao visual (identidade Vector, layout) precisa ser feita rodando
o servidor localmente e abrindo no navegador.

O `Client` padrao do Django (`enforce_csrf_checks=False`) NAO valida CSRF —
por isso o bug real de producao (HTMX nao mandava o token, 403 Forbidden em
qualquer POST) passou batido pelos testes originais. Os testes de
`TestClient(enforce_csrf_checks=True)` abaixo cobrem esse cenario.
"""

from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest
from django.test import Client

from apps.cadastro.models import ClasseAtivo, Gatilho, Oficina, TipoPreventiva
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
def classe(org) -> ClasseAtivo:
    return ClasseAtivo.objects.create(organizacao=org, nome="Trator", unidade="Horas")


def test_index_cria_conjunto_premissas_padrao(client, org):
    assert not ConjuntoPremissas.objects.for_org(org).exists()
    resposta = client.get(f"/{org.slug}/premissas/")
    assert resposta.status_code == 200
    assert ConjuntoPremissas.objects.for_org(org).filter(vigente=True).exists()


def test_index_lista_oficinas_e_classes(client, org, oficina, classe):
    resposta = client.get(f"/{org.slug}/premissas/")
    conteudo = resposta.content.decode()
    assert oficina.nome in conteudo
    assert classe.nome in conteudo


def test_index_mostra_horas_liquidas_calculadas_pelo_motor(client, org, oficina):
    """A tela chama apps/motor/horas.py — nao reimplementa a formula.

    Numero aparece no formato brasileiro (vírgula decimal) — Django localiza
    automaticamente para LANGUAGE_CODE="pt-br" (skill vector-relatorios:
    "números formato brasileiro").
    """
    resposta = client.get(f"/{org.slug}/premissas/")
    conteudo = resposta.content.decode()
    # ef = max(0, 8.8-1.2-0.17-0.25) = 7.18 (SPEC_Funcional.md SS3.1)
    assert "7,18" in conteudo


def test_atualizar_indices_persiste_no_banco(client, org, oficina):
    resposta = client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/",
        {"campo": "prev_pct", "valor": "75"},
    )
    assert resposta.status_code == 200
    oficina.refresh_from_db()
    assert oficina.prev_pct == Decimal("75")


def test_atualizar_indices_aceita_decimal_com_virgula(client, org, oficina):
    resposta = client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/",
        {"campo": "deflator_pct", "valor": "4,5"},
    )
    assert resposta.status_code == 200
    oficina.refresh_from_db()
    assert oficina.deflator_pct == Decimal("4.5")


def test_atualizar_indices_campo_invalido_retorna_400(client, org, oficina):
    resposta = client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/",
        {"campo": "campo_que_nao_existe", "valor": "1"},
    )
    assert resposta.status_code == 400


def test_atualizar_disp_persiste_no_json(client, org, oficina):
    resposta = client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/disp/",
        {"campo": "h_brutas", "valor": "9.0"},
    )
    assert resposta.status_code == 200
    oficina.refresh_from_db()
    assert oficina.disp_mo["h_brutas"] == 9.0
    # demais chaves do JSON preservadas
    assert oficina.disp_mo["almoco"] == 1.2


def test_valor_no_input_usa_ponto_nao_virgula_decimal(client, org, oficina):
    """Reproduz o bug relatado: LANGUAGE_CODE="pt-br" faz Django renderizar
    `{{ valor }}` com vírgula ("0,25"), mas <input type="number"> exige ponto
    decimal (HTML5) — com vírgula o navegador rejeita o valor silenciosamente
    e o campo aparece vazio ao recarregar a página. `_campo_numero.html` e
    `index.html` devem usar `|unlocalize`.
    """
    resposta_post = client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/disp/",
        {"campo": "abr_os", "valor": "0.25"},
    )
    conteudo_post = resposta_post.content.decode()
    assert 'value="0.25"' in conteudo_post
    assert "0,25" not in conteudo_post

    conteudo_get = client.get(f"/{org.slug}/premissas/").content.decode()
    assert 'value="0.25"' in conteudo_get
    assert "0,25" not in conteudo_get


def test_horas_liquidas_calculadas_continuam_em_formato_brasileiro(client, org, oficina):
    """As celulas so-leitura (nao sao <input>) devem continuar com vírgula —
    formato brasileiro exigido para exibição (skill vector-relatorios)."""
    conteudo = client.get(f"/{org.slug}/premissas/").content.decode()
    assert "7,18" in conteudo  # HORAS EFETIVAS/DIA — ver fixture `oficina`


def test_atualizar_calendario_mes_dias_uteis(client, org):
    client.get(f"/{org.slug}/premissas/")  # garante ConjuntoPremissas criado
    resposta = client.post(
        f"/{org.slug}/premissas/calendario/mes/",
        {"campo": "dias_uteis", "indice": "0", "valor": "20"},
    )
    assert resposta.status_code == 200
    conjunto = ConjuntoPremissas.objects.for_org(org).get(vigente=True)
    assert conjunto.calendario["dias_uteis"][0] == 20


def test_atualizar_calendario_mes_sazonal(client, org):
    client.get(f"/{org.slug}/premissas/")
    resposta = client.post(
        f"/{org.slug}/premissas/calendario/mes/",
        {"campo": "sazonal", "indice": "5", "valor": "1,4"},
    )
    assert resposta.status_code == 200
    conjunto = ConjuntoPremissas.objects.for_org(org).get(vigente=True)
    assert conjunto.calendario["sazonal"][5] == 1.4


def test_atualizar_calendario_mes_indice_invalido(client, org):
    client.get(f"/{org.slug}/premissas/")
    resposta = client.post(
        f"/{org.slug}/premissas/calendario/mes/",
        {"campo": "dias_uteis", "indice": "99", "valor": "20"},
    )
    assert resposta.status_code == 400


def test_alternar_safra_mes(client, org):
    client.get(f"/{org.slug}/premissas/")
    conjunto = ConjuntoPremissas.objects.for_org(org).get(vigente=True)
    valor_inicial = conjunto.calendario["safra"][2]

    resposta = client.post(f"/{org.slug}/premissas/calendario/safra/", {"indice": "2"})
    assert resposta.status_code == 200

    conjunto.refresh_from_db()
    assert conjunto.calendario["safra"][2] != valor_inicial


def test_atualizar_datas_safra(client, org):
    client.get(f"/{org.slug}/premissas/")
    resposta = client.post(
        f"/{org.slug}/premissas/calendario/datas/",
        {"inicio_safra": "2026-09-01", "fim_safra": "2027-03-31"},
    )
    assert resposta.status_code == 200
    conjunto = ConjuntoPremissas.objects.for_org(org).get(vigente=True)
    assert conjunto.calendario["inicio_safra"] == "2026-09-01"
    assert conjunto.calendario["fim_safra"] == "2027-03-31"


def test_atualizar_gatilho_cria(client, org, classe):
    resposta = client.post(
        f"/{org.slug}/premissas/gatilho/{classe.pk}/",
        {"tipo": "S", "intervalo": "250"},
    )
    assert resposta.status_code == 200
    gatilho = Gatilho.objects.get(classe=classe, tipo="S")
    assert gatilho.intervalo == Decimal("250.00")
    assert gatilho.ordem == 0


def test_atualizar_gatilho_remove_quando_vazio(client, org, classe):
    Gatilho.objects.create(organizacao=org, classe=classe, tipo=TipoPreventiva.A, intervalo=500)
    resposta = client.post(
        f"/{org.slug}/premissas/gatilho/{classe.pk}/",
        {"tipo": "A", "intervalo": ""},
    )
    assert resposta.status_code == 200
    assert not Gatilho.objects.filter(classe=classe, tipo="A").exists()


def test_atualizar_classe_unidade(client, org, classe):
    resposta = client.post(
        f"/{org.slug}/premissas/classe/{classe.pk}/unidade/",
        {"unidade": "KM"},
    )
    assert resposta.status_code == 200
    classe.refresh_from_db()
    assert classe.unidade == "KM"


def test_get_nao_permitido_em_endpoints_de_atualizacao(client, org, oficina):
    resposta = client.get(f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/")
    assert resposta.status_code == 405


def test_organizacao_inexistente_retorna_404(client):
    resposta = client.get("/organizacao-que-nao-existe/premissas/")
    assert resposta.status_code == 404


def test_pagina_inclui_csrf_token_para_htmx(client, org):
    """base.html manda `hx-headers` com X-CSRFToken no <body> — sem isso, HTMX
    nao envia CSRF e todo POST vira 403 (bug real reportado em producao)."""
    conteudo = client.get(f"/{org.slug}/premissas/").content.decode()
    assert "hx-headers" in conteudo
    assert "X-CSRFToken" in conteudo


def test_atualizar_indices_com_csrf_ativo_como_htmx_enviaria(org, oficina):
    """Reproduz o fluxo real do navegador: cliente com CSRF habilitado, token
    obtido do cookie (setado ao renderizar `{{ csrf_token }}`) e enviado via
    header X-CSRFToken — exatamente como `hx-headers` faz."""
    csrf_client = Client(enforce_csrf_checks=True)
    resposta_pagina = csrf_client.get(f"/{org.slug}/premissas/")
    token = resposta_pagina.cookies["csrftoken"].value

    resposta = csrf_client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/",
        {"campo": "prev_pct", "valor": "80"},
        HTTP_X_CSRFTOKEN=token,
    )

    assert resposta.status_code == 200
    oficina.refresh_from_db()
    assert oficina.prev_pct == Decimal("80")


def test_atualizar_indices_sem_csrf_token_e_rejeitado(org, oficina):
    """Reproduz o bug relatado: POST sem o header X-CSRFToken -> 403 Forbidden."""
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.get(f"/{org.slug}/premissas/")  # garante cookie csrftoken setado

    resposta = csrf_client.post(
        f"/{org.slug}/premissas/oficina/{oficina.pk}/indices/",
        {"campo": "prev_pct", "valor": "80"},
    )

    assert resposta.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_atualizar_disp_concorrente_nao_perde_atualizacoes(org, oficina):
    """Reproduz o bug relatado: usuario tabulando rapido por varios campos de
    disponibilidade da MESMA oficina disparava POSTs quase simultaneos; sem
    lock de linha (`select_for_update`), cada um lia o `disp_mo` antes de
    qualquer salvar, e o ultimo `save()` apagava as mudancas dos outros.
    Reproduzido empiricamente antes da correcao: de 8 campos enviados em
    paralelo, 1 sempre se perdia. `transaction=True` roda commits reais em
    threads separadas (o marcador `django_db` padrao do modulo usaria uma
    unica transacao por teste, o que mascararia a race).
    """
    csrf_client = Client(enforce_csrf_checks=True)
    resposta_pagina = csrf_client.get(f"/{org.slug}/premissas/")
    token = resposta_pagina.cookies["csrftoken"].value
    cookies = resposta_pagina.cookies

    campos = [
        ("h_brutas", "8.8"),
        ("almoco", "1.2"),
        ("cafe", "0.17"),
        ("prod", "80"),
        ("abs", "5"),
        ("ferias", "8.33"),
        ("trein", "16"),
        ("abr_os", "0.25"),
    ]

    def enviar(campo_valor):
        campo, valor = campo_valor
        cliente = Client()
        cliente.cookies = cookies
        return cliente.post(
            f"/{org.slug}/premissas/oficina/{oficina.pk}/disp/",
            {"campo": campo, "valor": valor},
            HTTP_X_CSRFTOKEN=token,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(campos)) as executor:
        resultados = list(executor.map(enviar, campos))

    assert all(r.status_code == 200 for r in resultados)

    oficina.refresh_from_db()
    for campo, valor in campos:
        assert oficina.disp_mo[campo] == pytest.approx(float(valor)), campo
