"""Testes de integracao dos importadores contra os arquivos REAIS em `Templates_Vector/`
(templates Vector) — nao sao amostras sinteticas, sao os arquivos que o
cliente efetivamente recebe/preenche.

Exige banco (Postgres — Procrastinate/JSONField) e cadastro previo de
Oficina/ClasseAtivo/Gatilho, igual a um ambiente real (importador nao cria
oficina/classe, ver docstring de `importadores/frota.py`).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.conf import settings

from apps.cadastro.models import (
    AtividadeMaterial,
    Ativo,
    ChecklistAtividade,
    ClasseAtivo,
    Gatilho,
    ItemMaterial,
    Oficina,
    Pessoa,
    TipoPreventiva,
)
from apps.core.models import Organizacao
from apps.importacao.calibracao import calcular_mix_prev_corr, calcular_sazonalidade
from apps.importacao.importadores.checklist import (
    importar_catalogo_itens,
    importar_checklist,
    importar_materiais_checklist,
)
from apps.importacao.importadores.frota import importar_frota
from apps.importacao.importadores.historico_os import importar_historico_os
from apps.importacao.importadores.pessoas import importar_pessoas
from apps.importacao.models import OrdemServico

pytestmark = pytest.mark.django_db

TEMPLATES_DIR = settings.BASE_DIR / "Templates_Vector"


@pytest.fixture
def organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Cliente Teste", slug="cliente-teste")


@pytest.fixture
def cadastro_base(organizacao):
    of_agricola = Oficina.objects.create(
        organizacao=organizacao, nome="Oficina Agrícola", prev_pct=60, corr_pct=40, deflator_pct=5
    )
    of_transporte = Oficina.objects.create(
        organizacao=organizacao, nome="Oficina Transporte", prev_pct=40, corr_pct=60, deflator_pct=5
    )
    unidades = {"Trator": "Horas", "Colhedora": "Horas", "Caminhão": "KM"}
    for nome_classe, unidade in unidades.items():
        classe = ClasseAtivo.objects.create(
            organizacao=organizacao, nome=nome_classe, unidade=unidade
        )
        Gatilho.objects.create(
            organizacao=organizacao, classe=classe, tipo=TipoPreventiva.S, intervalo=250, ordem=0
        )
    return {"Oficina Agrícola": of_agricola, "Oficina Transporte": of_transporte}


def test_importar_frota_real(organizacao, cadastro_base):
    resultado = importar_frota(organizacao, TEMPLATES_DIR / "template_frota.xlsx")

    assert resultado.erros == []
    assert resultado.importados == 3
    assert Ativo.objects.for_org(organizacao).count() == 3

    trator = Ativo.objects.for_org(organizacao).get(id_externo="TRA-001")
    assert trator.nome == "Trator John Deere 7215R"
    assert trator.tipo_gatilho == "Horas"
    assert trator.uso_atual == Decimal("4250")
    assert trator.setor is not None
    assert trator.setor.nome == "CMN-01"
    assert trator.setor.filial.nome == "Fazenda Norte"
    assert trator.intervalo == Decimal("250.00")

    caminhao = Ativo.objects.for_org(organizacao).get(id_externo="CAM-001")
    assert caminhao.tipo_gatilho == "KM"


def test_importar_frota_rejeita_oficina_desconhecida(organizacao):
    """Sem oficina/classe cadastradas, todas as linhas devem virar erro reportado
    (nunca uma excecao que aborta o import inteiro)."""
    resultado = importar_frota(organizacao, TEMPLATES_DIR / "template_frota.xlsx")
    assert resultado.importados == 0
    assert resultado.total_linhas == 3
    assert len(resultado.erros) == 3


def test_importar_pessoas_real(organizacao, cadastro_base):
    resultado = importar_pessoas(organizacao, TEMPLATES_DIR / "template_pessoas.xlsx")

    assert resultado.erros == []
    assert resultado.importados == 4
    assert Pessoa.objects.for_org(organizacao).count() == 4

    joao = Pessoa.objects.for_org(organizacao).get(id_externo="F-0142")
    assert joao.nome == "João da Silva"  # mojibake corrigido
    assert joao.oficina.nome == "Oficina Agrícola"
    assert joao.salario == Decimal("4500")

    roberto = Pessoa.objects.for_org(organizacao).get(id_externo="F-0145")
    assert roberto.turno == "12x36"  # fora das choices sugeridas, mas aceito


def test_importar_catalogo_itens_real(organizacao):
    resultado = importar_catalogo_itens(organizacao, TEMPLATES_DIR / "template_catalogo_itens.xlsx")

    assert resultado.erros == []
    assert resultado.importados == 15
    assert ItemMaterial.objects.for_org(organizacao).filter(tipo="insumo").count() == 10
    assert ItemMaterial.objects.for_org(organizacao).filter(tipo="peca").count() == 5

    oleo = ItemMaterial.objects.for_org(organizacao).get(id_externo="INS-001")
    assert oleo.descricao == "Óleo Motor 15W40"
    assert oleo.custo_unitario == Decimal("28.50")


def test_importar_checklist_real(organizacao, cadastro_base):
    resultado = importar_checklist(organizacao, TEMPLATES_DIR / "template_checklist.xlsx")

    assert resultado.erros == []
    assert resultado.importados == 11
    assert ChecklistAtividade.objects.for_org(organizacao).count() == 11

    primeira = ChecklistAtividade.objects.for_org(organizacao).get(
        id_checklist="CKL-A-TRA", id_externo="ATI-001"
    )
    assert primeira.tipo_prev == "A"
    assert primeira.classe.nome == "Trator"
    assert primeira.hh == Decimal("0.50")
    assert primeira.cargo == "Mecânico"

    # ATI-001 ("troca de óleo") se repete em CKL-A-TRA e CKL-B-TRA — a
    # heranca cumulativa (S⊂A⊂B) faz o mesmo item aparecer em varias
    # revisões; a chave natural e (id_checklist, id_atividade), nao so
    # id_atividade.
    segunda = ChecklistAtividade.objects.for_org(organizacao).get(
        id_checklist="CKL-B-TRA", id_externo="ATI-001"
    )
    assert segunda.tipo_prev == "B"
    assert primeira.pk != segunda.pk


def test_importar_materiais_checklist_real(organizacao, cadastro_base):
    importar_checklist(organizacao, TEMPLATES_DIR / "template_checklist.xlsx")
    importar_catalogo_itens(organizacao, TEMPLATES_DIR / "template_catalogo_itens.xlsx")

    resultado = importar_materiais_checklist(
        organizacao, TEMPLATES_DIR / "template_pecas_insumos.xlsx"
    )

    assert resultado.erros == []
    assert resultado.importados == 7
    assert AtividadeMaterial.objects.for_org(organizacao).count() == 7

    vinculo = AtividadeMaterial.objects.for_org(organizacao).get(
        atividade__id_checklist="CKL-A-TRA",
        atividade__id_externo="ATI-001",
        item__id_externo="INS-001",
    )
    assert vinculo.qtd == Decimal("7.000")


def test_importar_materiais_checklist_sem_dependencias_reporta_erro(organizacao):
    """Sem checklist/catalogo importados antes, cada linha deve virar erro claro."""
    resultado = importar_materiais_checklist(
        organizacao, TEMPLATES_DIR / "template_pecas_insumos.xlsx"
    )
    assert resultado.importados == 0
    assert len(resultado.erros) == 7


def test_importar_historico_os_real(organizacao, cadastro_base):
    importar_frota(organizacao, TEMPLATES_DIR / "template_frota.xlsx")

    resultado = importar_historico_os(organizacao, TEMPLATES_DIR / "template_historico_os.xlsx")

    assert resultado.erros == []
    assert resultado.importados == 5
    assert OrdemServico.objects.for_org(organizacao).count() == 5

    primeira = OrdemServico.objects.for_org(organizacao).get(id_externo="OS-24-0891")
    assert primeira.ativo.id_externo == "TRA-001"
    assert primeira.tipo_os == "Corretiva_Oficina"
    assert primeira.custo_total == Decimal("560.00")


def test_calibracao_sobre_historico_os_importado(organizacao, cadastro_base):
    importar_frota(organizacao, TEMPLATES_DIR / "template_frota.xlsx")
    importar_historico_os(organizacao, TEMPLATES_DIR / "template_historico_os.xlsx")

    ordens = list(OrdemServico.objects.for_org(organizacao).select_related("oficina"))
    mix = calcular_mix_prev_corr(ordens)
    sazonal = calcular_sazonalidade(ordens)

    # As 5 OS do template sao todas Corretiva_* ou Reforma (nao classificada) —
    # nenhuma e Preventiva, entao o mix esperado e 100% corretiva onde houver dado.
    assert mix["Oficina Agrícola"].corr_pct == 100.0
    assert mix["Oficina Transporte"].corr_pct == 100.0
    assert len(sazonal) == 12
