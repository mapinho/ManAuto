"""Testes dos utilitarios de parsing (apps/importacao/parsing.py) — sem banco."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import openpyxl
import pytest

from apps.importacao.parsing import (
    ler_linhas,
    normalizar_mojibake,
    parse_bool,
    parse_data,
    parse_decimal,
    parse_int,
)


def test_normalizar_mojibake_corrige_utf8_mal_decodificado():
    assert normalizar_mojibake("JoÃ£o da Silva") == "João da Silva"
    assert normalizar_mojibake("Oficina AgrÃ\xadcola") == "Oficina Agrícola"


def test_normalizar_mojibake_preserva_texto_ja_correto():
    assert normalizar_mojibake("João da Silva") == "João da Silva"
    assert normalizar_mojibake("") == ""
    assert normalizar_mojibake(None) is None


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("28.50", Decimal("28.50")),
        ("28,50", Decimal("28.50")),
        ("1.234,56", Decimal("1234.56")),
        (7, Decimal(7)),
        (0.5, Decimal("0.5")),
    ],
)
def test_parse_decimal_aceita_ponto_e_virgula(valor, esperado):
    assert parse_decimal(valor) == esperado


def test_parse_decimal_vazio_usa_padrao():
    assert parse_decimal(None, padrao=Decimal(0)) == Decimal(0)
    assert parse_decimal("", padrao=Decimal(0)) == Decimal(0)


def test_parse_decimal_vazio_sem_padrao_falha():
    with pytest.raises(ValueError):
        parse_decimal(None)


def test_parse_decimal_invalido_falha():
    with pytest.raises(ValueError):
        parse_decimal("abc")


def test_parse_int_e_parse_bool():
    assert parse_int("7") == 7
    assert parse_int(None, padrao=0) == 0
    assert parse_bool("true") is True
    assert parse_bool("false") is False
    assert parse_bool("Sim") is True
    assert parse_bool("Não") is False


def test_parse_data_aceita_datetime_date_e_string():
    assert parse_data(datetime(2025, 4, 1)) == date(2025, 4, 1)
    assert parse_data(date(2025, 4, 1)) == date(2025, 4, 1)
    assert parse_data("2025-04-01") == date(2025, 4, 1)
    assert parse_data("01/04/2025") == date(2025, 4, 1)


def test_parse_data_invalida_falha():
    with pytest.raises(ValueError):
        parse_data("não é uma data")


def test_ler_linhas_xlsx(tmp_path):
    caminho = tmp_path / "amostra.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nome", "valor"])
    ws.append(["Item A", 10])
    ws.append(["Item B", 20])
    wb.save(caminho)

    linhas = list(ler_linhas(caminho))
    assert linhas == [
        (2, {"nome": "Item A", "valor": 10}),
        (3, {"nome": "Item B", "valor": 20}),
    ]


def test_ler_linhas_csv_com_bom(tmp_path):
    caminho = tmp_path / "amostra.csv"
    caminho.write_bytes("nome,valor\nItem A,10\nItem B,20\n".encode("utf-8-sig"))

    linhas = list(ler_linhas(caminho))
    assert linhas == [
        (2, {"nome": "Item A", "valor": "10"}),
        (3, {"nome": "Item B", "valor": "20"}),
    ]


def test_ler_linhas_ignora_linhas_totalmente_vazias(tmp_path):
    caminho = tmp_path / "amostra.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nome", "valor"])
    ws.append(["Item A", 10])
    ws.append([None, None])
    ws.append(["Item B", 20])
    wb.save(caminho)

    linhas = list(ler_linhas(caminho))
    assert [n for n, _ in linhas] == [2, 4]
