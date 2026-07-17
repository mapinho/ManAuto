"""Agenda de preventivas em datas reais — SPEC_Funcional.md modulo 6.

Oficina principal = maior HH na heranca do tipo acionado; mecanico responsavel
por round-robin na oficina; data = dias uteis da semana, round-robin por semana.
"""

from __future__ import annotations

from datetime import date, timedelta

from .cronograma import calc_cronograma_semanal
from .heranca import get_itens_checklist
from .tipos import Ativo, EventoAgenda, ItemChecklist, Pessoa, Premissas

_OFICINA_PADRAO = "Mec. Oficina"


def dias_uteis_da_semana(inicio_semana: date) -> list[date]:
    dias = [inicio_semana + timedelta(days=i) for i in range(7)]
    uteis = [d for d in dias if d.weekday() <= 4]  # segunda(0)..sexta(4)
    return uteis or [inicio_semana]


def build_agenda_eventos(
    frota: list[Ativo],
    premissas: Premissas,
    checklist: list[ItemChecklist],
    pessoas: list[Pessoa],
) -> list[EventoAgenda]:
    grid, semanas = calc_cronograma_semanal(frota, premissas, checklist)
    semana_por_idx = {s.idx: s for s in semanas}
    eventos: list[EventoAgenda] = []
    round_robin = {of: 0 for of in premissas.oficinas}
    contador_semana: dict[int, int] = {}

    for ativo in frota:
        if ativo.status != "Ativo":
            continue
        ag = grid.get(ativo.id, {})
        for wi in sorted(ag.keys()):
            entrada = ag[wi]
            sem = semana_por_idx.get(wi)
            if sem is None:
                continue

            itens = get_itens_checklist(ativo.classe, entrada.tipo, checklist, premissas.heranca)
            hh_por_oficina: dict[str, float] = {}
            for item in itens:
                hh_por_oficina[item.oficina] = hh_por_oficina.get(item.oficina, 0.0) + item.hh
            oficina = (
                max(hh_por_oficina.items(), key=lambda kv: kv[1])[0]
                if hh_por_oficina
                else _OFICINA_PADRAO
            )

            equipe = [p for p in pessoas if p.oficina == oficina and p.status == "Ativo"]
            if equipe:
                mecanico = equipe[round_robin[oficina] % len(equipe)].nome
                round_robin[oficina] = round_robin.get(oficina, 0) + 1
            else:
                mecanico = f"Equipe {oficina}"

            dias = dias_uteis_da_semana(sem.data)
            k = contador_semana.get(wi, 0)
            contador_semana[wi] = k + 1
            data_evento = dias[k % len(dias)]

            eventos.append(
                EventoAgenda(
                    data=data_evento,
                    ativo=ativo.nome,
                    classe=ativo.classe,
                    tipo=entrada.tipo,
                    hh=entrada.hh,
                    count=entrada.count,
                    oficina=oficina,
                    mecanico=mecanico,
                    semana_idx=wi,
                    safra=sem.safra,
                )
            )

    eventos.sort(key=lambda e: e.data)
    return eventos
