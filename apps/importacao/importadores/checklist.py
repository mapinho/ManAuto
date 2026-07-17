"""Importadores de Checklist e materiais — templates Vector.

Tres arquivos, com dependencia de ordem (cada um exige o anterior já
importado):
1. `template_catalogo_itens.xlsx` -> `importar_catalogo_itens` (ItemMaterial)
2. `template_checklist.xlsx` -> `importar_checklist` (ChecklistAtividade)
3. `template_pecas_insumos.xlsx` -> `importar_materiais_checklist` (AtividadeMaterial,
   vincula por id_atividade/id_item — exige 1 e 2 já carregados)

Classe e Oficina precisam existir previamente no cadastro (mesma razao do
importador de Frota).
"""

from __future__ import annotations

from decimal import Decimal

from apps.cadastro.models import ChecklistAtividade, ClasseAtivo, ItemMaterial, Oficina
from apps.core.models import Organizacao

from ..parsing import ResultadoImportacao, campo_obrigatorio, ler_linhas, parse_decimal, parse_int


def _classificar_tipo_item(id_item: str, tipo_item: str) -> str:
    """`id_item` segue o prefixo INS-/PEC- nos templates Vector; usa o texto
    de `tipo_item` como reserva quando o prefixo nao e reconhecido.
    """
    prefixo = id_item.split("-")[0].strip().upper() if id_item else ""
    if prefixo == "INS":
        return ItemMaterial.Tipo.INSUMO
    if prefixo == "PEC":
        return ItemMaterial.Tipo.PECA
    texto = (tipo_item or "").strip().lower()
    if "peça" in texto or "peca" in texto:
        return ItemMaterial.Tipo.PECA
    return ItemMaterial.Tipo.INSUMO


def importar_catalogo_itens(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_externo = str(campo_obrigatorio(registro, "id_item"))
            descricao = str(campo_obrigatorio(registro, "descricao_item"))
            unidade = str(campo_obrigatorio(registro, "unidade"))
            custo_unitario = parse_decimal(registro.get("custo_unitario"), padrao=Decimal(0))
            tipo_item = str(registro.get("tipo_item") or "")

            defaults = {
                "descricao": descricao,
                "tipo": _classificar_tipo_item(id_externo, tipo_item),
                "subtipo": tipo_item,
                "unidade": unidade,
                "custo_unitario": custo_unitario,
                "fornecedor_principal": str(registro.get("fornecedor_principal") or ""),
                "codigo_fabricante": str(registro.get("codigo_fabricante") or ""),
                "observacao": str(registro.get("observacao") or ""),
                "origem_arquivo": origem_arquivo,
            }
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            ItemMaterial.objects.update_or_create(
                organizacao=organizacao, id_externo=id_externo, defaults=defaults
            )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado


def importar_checklist(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_checklist = str(campo_obrigatorio(registro, "id_checklist"))
            id_externo = str(campo_obrigatorio(registro, "id_atividade"))
            nome_classe = str(campo_obrigatorio(registro, "classe_ativo"))
            nome_oficina = str(campo_obrigatorio(registro, "oficina"))
            tipo_prev = str(campo_obrigatorio(registro, "tipo_preventiva"))
            descricao = str(campo_obrigatorio(registro, "descricao_atividade"))
            hh = parse_decimal(campo_obrigatorio(registro, "hh"))

            classe = ClasseAtivo.objects.for_org(organizacao).filter(nome=nome_classe).first()
            if classe is None:
                raise ValueError(f"classe '{nome_classe}' não cadastrada")
            oficina = Oficina.objects.for_org(organizacao).filter(nome=nome_oficina).first()
            if oficina is None:
                raise ValueError(f"oficina '{nome_oficina}' não cadastrada")

            defaults = {
                "classe": classe,
                "tipo_prev": tipo_prev,
                "oficina": oficina,
                "nome_checklist": str(registro.get("nome_checklist") or ""),
                "seq": parse_int(registro.get("seq"), padrao=0),
                "descricao": descricao,
                "cargo": str(registro.get("tipo_mo") or ""),
                "tipo_atividade": str(registro.get("tipo_atividade") or ""),
                "hh": hh,
                "observacao": str(registro.get("observacao") or ""),
                "origem_arquivo": origem_arquivo,
            }
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            ChecklistAtividade.objects.update_or_create(
                organizacao=organizacao,
                id_checklist=id_checklist,
                id_externo=id_externo,
                defaults=defaults,
            )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado


def importar_materiais_checklist(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    from apps.cadastro.models import AtividadeMaterial

    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_checklist = str(campo_obrigatorio(registro, "id_checklist"))
            id_atividade = str(campo_obrigatorio(registro, "id_atividade"))
            id_item = str(campo_obrigatorio(registro, "id_item"))
            unidade = str(campo_obrigatorio(registro, "unidade"))
            qtd = parse_decimal(campo_obrigatorio(registro, "quantidade"))

            atividade = (
                ChecklistAtividade.objects.for_org(organizacao)
                .filter(id_checklist=id_checklist, id_externo=id_atividade)
                .first()
            )
            if atividade is None:
                raise ValueError(
                    f"atividade '{id_atividade}' do checklist '{id_checklist}' não encontrada"
                )
            item = ItemMaterial.objects.for_org(organizacao).filter(id_externo=id_item).first()
            if item is None:
                raise ValueError(f"item de material '{id_item}' não encontrado")
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            AtividadeMaterial.objects.update_or_create(
                organizacao=organizacao,
                atividade=atividade,
                item=item,
                defaults={"qtd": qtd, "unidade": unidade},
            )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado
