"""Arredondamento compativel com Math.round do JavaScript (fonte original do motor).

Math.round(x) do JS equivale a floor(x + 0.5) para qualquer sinal — diferente do
round() nativo do Python, que usa banker's rounding (arredonda .5 para o par mais
proximo). Usar round() built-in aqui quebraria a paridade numerica exigida pelos
fixtures de regressao (SPEC_Funcional.md SS3.6).
"""

import math


def round_js(n: float | None) -> float:
    n = n or 0.0
    return math.floor(n + 0.5) if n >= 0 else -math.floor(-n + 0.5)


def r2(n: float | None) -> float:
    n = n or 0.0
    return round_js(n * 100) / 100


def r1(n: float | None) -> float:
    n = n or 0.0
    return round_js(n * 10) / 10
