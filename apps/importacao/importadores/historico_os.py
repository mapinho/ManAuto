"""Importador de Historico de OS — `template_historico_os.xlsx` (templates Vector).

Colunas: id_os, id_ativo, data_abertura, data_fechamento, tipo_os, oficina,
sistema_falha, descricao_falha, hh_executadas, tipo_mo, custo_hh,
custo_pecas, custo_total, mecanico_responsavel, medicao_na_os.

So id_os, data_abertura e tipo_os sao obrigatorios: `ativo`/`oficina` ficam
None quando nao encontrados (nao rejeita a linha) — a OS ainda tem valor
para a calibracao (apps/importacao/calibracao.py) mesmo sem o vinculo, e
"dados sujos" (hh_executadas=0, custo_total inconsistente, horimetro
zerado) sao esperados nesta fonte (skill agrovector-dados).
"""

from __future__ import annotations

from decimal import Decimal

from apps.cadastro.models import Ativo, Oficina
from apps.core.models import Organizacao
from apps.importacao.models import OrdemServico

from ..parsing import ResultadoImportacao, campo_obrigatorio, ler_linhas, parse_data, parse_decimal


def importar_historico_os(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_externo = str(campo_obrigatorio(registro, "id_os"))
            data_abertura = parse_data(campo_obrigatorio(registro, "data_abertura"))
            tipo_os = str(campo_obrigatorio(registro, "tipo_os"))

            id_ativo = str(registro.get("id_ativo") or "")
            ativo = (
                Ativo.objects.for_org(organizacao).filter(id_externo=id_ativo).first()
                if id_ativo
                else None
            )
            nome_oficina = str(registro.get("oficina") or "")
            oficina = (
                Oficina.objects.for_org(organizacao).filter(nome=nome_oficina).first()
                if nome_oficina
                else None
            )

            defaults = {
                "ativo": ativo,
                "oficina": oficina,
                "tipo_os": tipo_os,
                "sistema_falha": str(registro.get("sistema_falha") or ""),
                "descricao_falha": str(registro.get("descricao_falha") or ""),
                "mecanico_responsavel": str(registro.get("mecanico_responsavel") or ""),
                "hh_executadas": parse_decimal(registro.get("hh_executadas"), padrao=Decimal(0)),
                "custo_hh": parse_decimal(registro.get("custo_hh"), padrao=Decimal(0)),
                "custo_pecas": parse_decimal(registro.get("custo_pecas"), padrao=Decimal(0)),
                "custo_total": parse_decimal(registro.get("custo_total"), padrao=Decimal(0)),
                "data": data_abertura,
                "origem_arquivo": origem_arquivo,
            }
            if registro.get("data_fechamento"):
                defaults["data_fechamento"] = parse_data(registro["data_fechamento"])
            if registro.get("medicao_na_os"):
                defaults["horimetro"] = parse_decimal(registro["medicao_na_os"])
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            OrdemServico.objects.update_or_create(
                organizacao=organizacao, id_externo=id_externo, defaults=defaults
            )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado
