"""Importador de Pessoas — `template_pessoas.xlsx` (templates Vector).

Colunas: id_funcionario, nome, cargo, tipo_mo, oficina, centro_manutencao,
filial, salario_base, encargos_pct, turno, horas_contratuais_dia, status.

Oficina precisa existir previamente (mesma razao do importador de Frota).
`turno` e gravado como veio da planilha mesmo que fora das opcoes sugeridas
em `Pessoa.Turno` (choices e so uma sugestao de UI, nao uma restricao de
banco) — turnos variam por cliente (ex.: "12x36") e nao vale a pena travar
o import por isso.
"""

from __future__ import annotations

from django.db import transaction

from apps.cadastro.models import Oficina, Pessoa
from apps.core.models import Organizacao

from ..common import obter_ou_criar_setor
from ..parsing import ResultadoImportacao, campo_obrigatorio, ler_linhas, parse_decimal


def importar_pessoas(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_externo = str(campo_obrigatorio(registro, "id_funcionario"))
            nome = str(campo_obrigatorio(registro, "nome"))
            nome_oficina = str(campo_obrigatorio(registro, "oficina"))
            turno = str(campo_obrigatorio(registro, "turno"))
            status = str(campo_obrigatorio(registro, "status"))
            salario = parse_decimal(campo_obrigatorio(registro, "salario_base"))
            encargos_pct = parse_decimal(campo_obrigatorio(registro, "encargos_pct"))

            oficina = Oficina.objects.for_org(organizacao).filter(nome=nome_oficina).first()
            if oficina is None:
                raise ValueError(f"oficina '{nome_oficina}' não cadastrada")

            nome_filial = str(registro.get("filial") or "").strip()
            nome_centro = str(registro.get("centro_manutencao") or "").strip()
            setor = (
                obter_ou_criar_setor(organizacao, nome_filial, nome_centro)
                if nome_filial and nome_centro
                else None
            )

            defaults = {
                "nome": nome,
                "oficina": oficina,
                "setor": setor,
                "cargo": str(registro.get("cargo") or ""),
                "tipo_mo": str(registro.get("tipo_mo") or ""),
                "turno": turno,
                "salario": salario,
                "encargos_pct": encargos_pct,
                "status": status,
                "origem_arquivo": origem_arquivo,
            }
            if registro.get("horas_contratuais_dia"):
                defaults["horas_contratuais_dia"] = parse_decimal(registro["horas_contratuais_dia"])
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            with transaction.atomic():
                Pessoa.objects.update_or_create(
                    organizacao=organizacao, id_externo=id_externo, defaults=defaults
                )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado
