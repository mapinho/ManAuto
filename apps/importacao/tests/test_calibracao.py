"""Testes da calibracao por historico de OS (apps/importacao/calibracao.py) — sem banco."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from apps.importacao.calibracao import (
    calcular_mix_prev_corr,
    calcular_sazonalidade,
    classificar_tipo_os,
    inferir_janela_safra,
)


@pytest.mark.parametrize(
    ("tipo_os", "esperado"),
    [
        ("Corretiva_Oficina", "CORR"),
        ("Corretiva_Campo", "CORR"),
        ("Falha operacional", "CORR"),
        ("Preventiva", "PREV"),
        ("Lavagem", "PREV"),
        ("Inspeção", "PREV"),
        ("Lubrificação", "PREV"),
        ("Preditiva", "PREV"),
        ("Parada programada", "PREV"),
        ("Reforma", None),
        ("", None),
    ],
)
def test_classificar_tipo_os(tipo_os, esperado):
    assert classificar_tipo_os(tipo_os) == esperado


def _os(oficina_nome: str | None, tipo_os: str, mes: int):
    oficina = SimpleNamespace(nome=oficina_nome) if oficina_nome else None
    return SimpleNamespace(oficina=oficina, tipo_os=tipo_os, data=date(2026, mes, 1))


def test_calcular_mix_prev_corr_por_oficina():
    ordens = [
        _os("Oficina A", "Preventiva", 1),
        _os("Oficina A", "Preventiva", 2),
        _os("Oficina A", "Corretiva_Oficina", 3),
        _os("Oficina B", "Corretiva_Campo", 1),
        _os(None, "Preventiva", 1),  # sem oficina: ignorada
        _os("Oficina A", "Reforma", 1),  # nao classificada: ignorada
    ]
    mix = calcular_mix_prev_corr(ordens)

    assert mix["Oficina A"].n_prev == 2
    assert mix["Oficina A"].n_corr == 1
    assert mix["Oficina A"].prev_pct == pytest.approx(66.67, abs=0.01)
    assert mix["Oficina A"].corr_pct == pytest.approx(33.33, abs=0.01)

    assert mix["Oficina B"].n_prev == 0
    assert mix["Oficina B"].n_corr == 1
    assert mix["Oficina B"].corr_pct == 100.0


def test_calcular_sazonalidade_media_um():
    ordens = [_os("Of", "Corretiva", mes) for mes in [1] * 24] + [
        _os("Of", "Corretiva", mes) for mes in range(1, 13)
    ]
    sazonal = calcular_sazonalidade(ordens)
    assert len(sazonal) == 12
    assert sazonal[0] > 1  # janeiro concentra bem mais OS que a media
    assert sum(sazonal) / 12 == pytest.approx(1.0, abs=0.2)


def test_calcular_sazonalidade_sem_corretivas_retorna_neutro():
    ordens = [_os("Of", "Preventiva", 1)]
    assert calcular_sazonalidade(ordens) == [1.0] * 12


def test_inferir_janela_safra():
    sazonal = [1.5, 1.2, 0.9, 0.5, 0.3, 0.3, 0.4, 0.8, 1.1, 1.4, 1.3, 1.3]
    janela = inferir_janela_safra(sazonal)
    assert janela == [f > 1 for f in sazonal]
    assert janela[0] is True
    assert janela[4] is False
