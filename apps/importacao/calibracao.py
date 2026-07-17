"""Calibracao por historico de OS — skill agrovector-dados, "Calibração por
histórico de OS (como feito para Petribú)".

1. Classificar tipo_os em PREV x CORR.
2. Mix por oficina: prev% = n_PREV/(n_PREV+n_CORR) (por contagem).
3. Sazonalidade: contagem de CORR por mês / média mensal (média = 1.0).
4. Inferir janela de safra pelos meses com fator > 1.

So calcula e devolve os numeros — aplicar o resultado em `Oficina`/
`ConjuntoPremissas` e uma decisao humana (consultor revisa antes de gravar),
nao e feito automaticamente aqui.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from apps.importacao.models import OrdemServico

_PREFIXOS_CORR = ("corretiva", "falha")
_PREFIXOS_PREV = ("preventiva", "lavagem", "inspe", "lubrific", "preditiva", "parada")


def classificar_tipo_os(tipo_os: str) -> str | None:
    """Retorna "PREV", "CORR" ou None (nao classificado — ex.: "Reforma",
    tratado como categoria propria e nao contado em nenhum dos dois lados
    do mix, ja que reforma nao e nem rotina preventiva nem corretiva comum).
    """
    chave = (tipo_os or "").strip().lower().replace("_", " ")
    if any(chave.startswith(p) for p in _PREFIXOS_CORR):
        return "CORR"
    if any(chave.startswith(p) for p in _PREFIXOS_PREV):
        return "PREV"
    return None


@dataclass(frozen=True)
class MixOficina:
    prev_pct: float
    corr_pct: float
    n_prev: int
    n_corr: int


def calcular_mix_prev_corr(ordens: Iterable[OrdemServico]) -> dict[str, MixOficina]:
    """`prev% = n_PREV / (n_PREV + n_CORR)` por oficina (contagem de OS)."""
    contagem: dict[str, dict[str, int]] = {}
    for os in ordens:
        if not os.oficina:
            continue
        tipo = classificar_tipo_os(os.tipo_os)
        if tipo is None:
            continue
        c = contagem.setdefault(os.oficina.nome, {"PREV": 0, "CORR": 0})
        c[tipo] += 1

    resultado: dict[str, MixOficina] = {}
    for nome_oficina, c in contagem.items():
        total = c["PREV"] + c["CORR"]
        if total == 0:
            continue
        resultado[nome_oficina] = MixOficina(
            prev_pct=round(c["PREV"] / total * 100, 2),
            corr_pct=round(c["CORR"] / total * 100, 2),
            n_prev=c["PREV"],
            n_corr=c["CORR"],
        )
    return resultado


def calcular_sazonalidade(ordens: Iterable[OrdemServico]) -> list[float]:
    """Contagem de OS corretivas por mes / media mensal (media global = 1.0)."""
    contagem_mes = [0] * 12
    for os in ordens:
        if classificar_tipo_os(os.tipo_os) != "CORR":
            continue
        contagem_mes[os.data.month - 1] += 1

    media = sum(contagem_mes) / 12
    if media == 0:
        return [1.0] * 12
    return [round(c / media, 2) for c in contagem_mes]


def inferir_janela_safra(sazonalidade: list[float]) -> list[bool]:
    """Meses com fator de sazonalidade > 1 sao inferidos como safra."""
    return [fator > 1 for fator in sazonalidade]
