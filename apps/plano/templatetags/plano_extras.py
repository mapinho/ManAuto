"""Filtro de indexacao dinamica — Django templates nao tem sintaxe nativa
`container[variavel]` (so `dict.chave_literal` ou `lista.0`), necessario
para colorir a grade do Cronograma pelo tipo de preventiva de cada celula
e para indexar a lista de meses por um numero calculado na view.
"""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def get_item(container, chave):
    try:
        return container[chave]
    except (KeyError, IndexError, TypeError):
        return None
