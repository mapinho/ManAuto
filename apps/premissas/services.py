"""Calendario vigente e horas liquidas por oficina — compartilhado entre telas.

Extraido de apps/premissas/views.py quando a tela de Pessoas passou a
precisar do mesmo calendario/disp_mo vigente para calcular custo/HH
(SPEC_Funcional.md SS3.1, formula 8) — Cronograma/Agenda/Disponibilidade
(proximas telas do roadmap) tambem vao depender disto. A view nunca
reimplementa a formula: quem calcula e sempre o motor (apps/motor/).
"""

from __future__ import annotations

from datetime import date

from apps.cadastro.models import ClasseAtivo, Oficina
from apps.core.models import Organizacao
from apps.motor.heranca import HERANCA_PADRAO
from apps.motor.horas import calc_horas_liquidas
from apps.motor.tipos import DispOficina, GatilhosClasse, HorasLiquidas, IndicesOficina, Premissas
from apps.motor.tipos import Gatilho as GatilhoMotor

from .models import ConjuntoPremissas

DISP_PADRAO = {
    "h_brutas": 8.8,
    "almoco": 1.0,
    "cafe": 0.17,
    "prod": 80,
    "abs": 5,
    "ferias": 8.33,
    "trein": 8,
    "abr_os": 0.17,
}

CALENDARIO_PADRAO = {
    "dias_uteis": [22] * 12,
    "safra": [False] * 12,
    "sazonal": [1.0] * 12,
    "inicio_safra": "2026-04-01",
    "fim_safra": "2026-11-30",
    "heranca": {tipo: list(itens) for tipo, itens in HERANCA_PADRAO.items()},
}


def conjunto_vigente(org: Organizacao, *, travar: bool = False) -> ConjuntoPremissas:
    """`travar=True` bloqueia a linha (SELECT ... FOR UPDATE) — exige rodar dentro
    de `transaction.atomic()`. Necessario em toda leitura-e-gravacao do JSON
    `calendario`: sem lock, dois POSTs quase simultaneos leem o mesmo JSON antes
    de qualquer um salvar, e o segundo `save()` sobrescreve a mudanca do
    primeiro (visto na pratica, ver historico do PR da tela de Premissas).
    """
    qs = ConjuntoPremissas.objects.for_org(org).filter(vigente=True).order_by("-versao")
    if travar:
        qs = qs.select_for_update()
    conjunto = qs.first()
    if conjunto is None:
        proxima_versao = (
            ConjuntoPremissas.objects.for_org(org)
            .order_by("-versao")
            .values_list("versao", flat=True)
            .first()
            or 0
        ) + 1
        conjunto = ConjuntoPremissas.objects.create(
            organizacao=org,
            versao=proxima_versao,
            vigente=True,
            calendario=dict(CALENDARIO_PADRAO),
        )
    return conjunto


def calendario(conjunto: ConjuntoPremissas) -> dict:
    return {**CALENDARIO_PADRAO, **conjunto.calendario}


def disp_oficina(oficina: Oficina) -> DispOficina:
    dados = {**DISP_PADRAO, **oficina.disp_mo}
    return DispOficina(
        h_brutas=float(dados["h_brutas"]),
        almoco=float(dados["almoco"]),
        cafe=float(dados["cafe"]),
        prod=float(dados["prod"]),
        abs_=float(dados["abs"]),
        ferias=float(dados["ferias"]),
        trein=float(dados["trein"]),
        abr_os=float(dados["abr_os"]),
    )


def horas_liquidas(oficina: Oficina) -> HorasLiquidas:
    """Chama o motor (apps/motor/horas.py) — nunca reimplementa a formula aqui."""
    return calc_horas_liquidas(disp_oficina(oficina))


def montar_premissas(org: Organizacao) -> Premissas:
    """Monta o `Premissas` do motor (apps/motor/tipos.py) a partir do cadastro
    vigente da organizacao — usado pelas telas/tarefas que rodam o motor
    (Cronograma, Agenda, Disponibilidade em apps/plano/)."""
    oficinas_qs = list(Oficina.objects.for_org(org).order_by("nome"))
    conjunto = conjunto_vigente(org)
    cal = calendario(conjunto)

    indices = {
        of.nome: IndicesOficina(
            prev=float(of.prev_pct),
            corr=float(of.corr_pct),
            deflator=float(of.deflator_pct),
            terceiros=float(of.terceiros_pct),
        )
        for of in oficinas_qs
    }
    disp = {of.nome: disp_oficina(of) for of in oficinas_qs}

    gatilhos = {}
    for classe in ClasseAtivo.objects.for_org(org).prefetch_related("gatilhos"):
        itvs = tuple(
            GatilhoMotor(valor=float(g.intervalo), tipo=g.tipo) for g in classe.gatilhos.all()
        )
        gatilhos[classe.nome] = GatilhosClasse(tipo_medida=classe.unidade, itvs=itvs)

    return Premissas(
        oficinas=tuple(of.nome for of in oficinas_qs),
        indices=indices,
        disp=disp,
        dias_uteis=tuple(cal["dias_uteis"]),
        safra=tuple(cal["safra"]),
        sazonal=tuple(cal["sazonal"]),
        gatilhos=gatilhos,
        inicio_safra=date.fromisoformat(cal["inicio_safra"]),
        fim_safra=date.fromisoformat(cal["fim_safra"]),
        heranca={tipo: tuple(itens) for tipo, itens in cal["heranca"].items()},
    )


__all__ = [
    "DISP_PADRAO",
    "CALENDARIO_PADRAO",
    "conjunto_vigente",
    "calendario",
    "disp_oficina",
    "horas_liquidas",
    "montar_premissas",
]
