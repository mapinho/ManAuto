"""Importador de Frota — `template_frota.xlsx` (templates Vector).

Colunas (ordem e um contrato, nao alterar): id_ativo, descricao, classe,
subclasse, ano_fabricacao, placa_serie, filial, centro_manutencao, oficina,
unidade_medicao, hodometro_atual, uso_medio_mensal, tipo_preventiva_atual,
ultima_prev_data, ultima_prev_medicao, status.

Oficina e Classe precisam existir previamente no cadastro (sao configuraveis
por organizacao e carregam indices/gatilhos que o importador nao pode
inventar) — linha com oficina/classe desconhecida e rejeitada. Filial e
Centro de Manutencao (mapeado para `core.Setor`) sao criados automaticamente
se ainda nao existirem, pois nao carregam configuracao propria.

O template so tem uma media mensal de uso (`uso_medio_mensal`), sem separar
safra/entressafra como o motor espera (`uso_sem_safra`/`uso_sem_entressafra`)
— dividimos igualmente pelas ~4,345 semanas do mes como uma aproximacao
inicial; o cliente pode refinar os dois valores depois via admin/tela de
cadastro.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.cadastro.models import Ativo, ClasseAtivo, Gatilho, Oficina, TipoPreventiva, Unidade
from apps.core.models import Organizacao

from ..common import obter_ou_criar_setor
from ..parsing import (
    ResultadoImportacao,
    campo_obrigatorio,
    ler_linhas,
    parse_data,
    parse_decimal,
)

_SEMANAS_POR_MES = Decimal("4.345")

_MAPA_UNIDADE = {
    "h": Unidade.HORAS,
    "horas": Unidade.HORAS,
    "km": Unidade.KM,
}


def _mapear_unidade(valor: str) -> str:
    chave = str(valor).strip().lower()
    if chave not in _MAPA_UNIDADE:
        raise ValueError(f"unidade_medicao desconhecida: {valor!r} (esperado 'H' ou 'KM')")
    return _MAPA_UNIDADE[chave]


def importar_frota(
    organizacao: Organizacao, caminho: str, *, origem_arquivo: str = ""
) -> ResultadoImportacao:
    resultado = ResultadoImportacao()

    for linha, registro in ler_linhas(caminho):
        resultado.total_linhas += 1
        try:
            id_externo = str(campo_obrigatorio(registro, "id_ativo"))
            nome = str(campo_obrigatorio(registro, "descricao"))
            nome_classe = str(campo_obrigatorio(registro, "classe"))
            nome_oficina = str(campo_obrigatorio(registro, "oficina"))
            status = str(campo_obrigatorio(registro, "status"))
            unidade = _mapear_unidade(campo_obrigatorio(registro, "unidade_medicao"))
            uso_atual = parse_decimal(campo_obrigatorio(registro, "hodometro_atual"))
            uso_medio_mensal = parse_decimal(registro.get("uso_medio_mensal"), padrao=Decimal(0))

            classe = ClasseAtivo.objects.for_org(organizacao).filter(nome=nome_classe).first()
            if classe is None:
                raise ValueError(f"classe '{nome_classe}' não cadastrada")
            oficina = Oficina.objects.for_org(organizacao).filter(nome=nome_oficina).first()
            if oficina is None:
                raise ValueError(f"oficina '{nome_oficina}' não cadastrada")
            gatilho_s = Gatilho.objects.filter(classe=classe, tipo=TipoPreventiva.S).first()
            if gatilho_s is None:
                raise ValueError(f"classe '{nome_classe}' sem gatilho S configurado")

            nome_filial = str(registro.get("filial") or "").strip()
            nome_centro = str(registro.get("centro_manutencao") or "").strip()
            setor = (
                obter_ou_criar_setor(organizacao, nome_filial, nome_centro)
                if nome_filial and nome_centro
                else None
            )

            tipo_prev_atual = str(registro.get("tipo_preventiva_atual") or "").strip()
            if tipo_prev_atual and tipo_prev_atual not in TipoPreventiva.values:
                raise ValueError(f"tipo_preventiva_atual inválido: {tipo_prev_atual!r}")

            uso_semanal = (uso_medio_mensal / _SEMANAS_POR_MES).quantize(Decimal("0.01"))

            defaults = {
                "nome": nome,
                "classe": classe,
                "setor": setor,
                "oficina": oficina,
                "subclasse": str(registro.get("subclasse") or ""),
                "placa_serie": str(registro.get("placa_serie") or ""),
                "ano": int(registro["ano_fabricacao"]) if registro.get("ano_fabricacao") else None,
                "status": status,
                "tipo_gatilho": unidade,
                "uso_atual": uso_atual,
                "uso_sem_safra": uso_semanal,
                "uso_sem_entressafra": uso_semanal,
                "intervalo": gatilho_s.intervalo,
                "tipo_preventiva_atual": tipo_prev_atual,
                "origem_arquivo": origem_arquivo,
            }
            if registro.get("ultima_prev_data"):
                defaults["ultima_prev_data"] = parse_data(registro["ultima_prev_data"])
            if registro.get("ultima_prev_medicao"):
                defaults["ultima_prev_medicao"] = parse_decimal(registro["ultima_prev_medicao"])
        except ValueError as exc:
            resultado.registrar_erro(linha, str(exc))
            continue

        try:
            with transaction.atomic():
                Ativo.objects.update_or_create(
                    organizacao=organizacao, id_externo=id_externo, defaults=defaults
                )
            resultado.importados += 1
        except Exception as exc:  # noqa: BLE001 - falha de persistencia vira erro de linha, nao aborta o import
            resultado.registrar_erro(linha, f"erro ao salvar: {exc}")

    return resultado
