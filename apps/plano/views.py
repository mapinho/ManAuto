"""Telas de Cronograma e Agenda — modulos 5 e 6 do roadmap R1
(SPEC_Tecnica_Ambiente.md SS6).

Ambas leem o mesmo `PlanoAnual` mais recente (persistido por
`apps/plano/services.py`) — Cronograma monta a grade semanal (ativo x 52
semanas) e o resumo mensal de HH por oficina; Agenda monta o calendario
mensal por datas reais e a lista cronologica de OS do trimestre
selecionado. Nenhuma das duas roda o motor no request (CLAUDE.md):
"Recalcular Plano" enfileira `apps/plano/tasks.py` via Procrastinate.
"""

from __future__ import annotations

import calendar
from datetime import date

from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.cadastro.models import Ativo, ClasseAtivo, Oficina, Pessoa
from apps.core.models import Organizacao
from apps.motor.semanas import Semana, gerar_semanas
from apps.plano.models import PlanoAnual
from apps.premissas import services as premissas_services

from .services import plano_vigente
from .tasks import task_recalcular_plano

_COR_TIPO = {"S": "#27c27a", "A": "#f59e0b", "B": "#ef4444", "C": "#a78bfa", "D": "#38bdf8"}
_LABEL_TIPO = {
    "S": "Simples",
    "A": "Intermediária",
    "B": "Completa",
    "C": "Grande porte",
    "D": "Reforma",
}
_MESES_LABEL = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_DOW = ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb")


def _get_org(org_slug: str) -> Organizacao:
    return get_object_or_404(Organizacao, slug=org_slug)


def _capacidade_semanal_total(org: Organizacao) -> float:
    total = 0.0
    for oficina in Oficina.objects.for_org(org):
        n_pessoas = Pessoa.objects.for_org(org).filter(
            oficina=oficina, status=Pessoa.Status.ATIVO
        ).count()
        liquidas = premissas_services.horas_liquidas(oficina).liquidas
        total += n_pessoas * 5 * liquidas
    return round(total, 2)


def _semanas_do_plano(plano: PlanoAnual) -> tuple[list[Semana], date]:
    cal = premissas_services.calendario(plano.conjunto_premissas)
    inicio_safra = date.fromisoformat(cal["inicio_safra"])
    fim_safra = date.fromisoformat(cal["fim_safra"])
    semanas = gerar_semanas(inicio_safra, fim_safra)
    return semanas, semanas[0].data


def _semana_idx(evento_data: date, inicio: date, n_semanas: int) -> int:
    return max(0, min(n_semanas - 1, (evento_data - inicio).days // 7))


def _nome_curto(nome: str) -> str:
    partes = nome.split("—")
    if len(partes) > 1:
        return partes[-1].strip()
    palavras = nome.split(" ")
    return palavras[-1] if palavras else nome


def cronograma(request, org_slug: str):
    org = _get_org(org_slug)
    plano = plano_vigente(org)

    if plano is None:
        return render(
            request,
            "plano/cronograma.html",
            {"org": org, "active_tab": "cronograma", "plano": None},
        )

    cal = premissas_services.calendario(plano.conjunto_premissas)
    semanas, inicio = _semanas_do_plano(plano)

    eventos = (
        plano.eventos.select_related("ativo", "ativo__classe")
        .order_by("ativo__classe__nome", "ativo__nome", "data")
    )

    grid: dict[int, dict[int, dict]] = {}
    hh_por_semana = [0.0] * len(semanas)
    total_hh = 0.0
    for evento in eventos:
        idx = _semana_idx(evento.data, inicio, len(semanas))
        celula = grid.setdefault(evento.ativo_id, {})
        celula[idx] = {"tipo": evento.tipo, "count": evento.count, "hh": float(evento.hh)}
        hh_por_semana[idx] += float(evento.hh)
        total_hh += float(evento.hh)

    capacidade_semanal = _capacidade_semanal_total(org)
    conflitos = sum(1 for h in hh_por_semana if capacidade_semanal and h > capacidade_semanal)

    classes = list(ClasseAtivo.objects.for_org(org).order_by("nome"))
    ativos_por_classe = []
    for classe in classes:
        ativos_classe = list(
            Ativo.objects.for_org(org).filter(classe=classe, status=Ativo.Status.ATIVO).order_by(
                "nome"
            )
        )
        if not ativos_classe:
            continue
        linhas = []
        for ativo in ativos_classe:
            celulas_ativo = grid.get(ativo.pk, {})
            primeira_semana = min(celulas_ativo) if celulas_ativo else None
            proxima = semanas[primeira_semana].label if primeira_semana is not None else "—"
            linhas.append(
                {
                    "ativo": ativo,
                    "celulas": [celulas_ativo.get(sem.idx) for sem in semanas],
                    "n_prev": len(celulas_ativo),
                    "proxima": proxima,
                }
            )
        ativos_por_classe.append({"classe": classe.nome, "linhas": linhas})

    hh_por_oficina = plano.hh_prev_por_oficina
    total_hh_mes = [0.0] * 12
    for valores in hh_por_oficina.values():
        for i, v in enumerate(valores):
            total_hh_mes[i] += v
    hh_por_oficina_lista = [
        {"nome": of, "valores": [round(v, 1) for v in valores], "anual": round(sum(valores), 1)}
        for of, valores in hh_por_oficina.items()
        if any(valores)
    ]
    legenda_tipos = [
        {"tipo": tipo, "cor": cor, "label": _LABEL_TIPO[tipo]} for tipo, cor in _COR_TIPO.items()
    ]

    meses_grp = []
    mes_atual = None
    for sem in semanas:
        if sem.mes != mes_atual:
            meses_grp.append({"mes": sem.mes, "safra": sem.safra, "semanas": [sem]})
            mes_atual = sem.mes
        else:
            meses_grp[-1]["semanas"].append(sem)

    contexto = {
        "org": org,
        "active_tab": "cronograma",
        "plano": plano,
        "semanas": semanas,
        "meses_grp": meses_grp,
        "ativos_por_classe": ativos_por_classe,
        "hh_por_semana": hh_por_semana,
        "capacidade_semanal": capacidade_semanal,
        "conflitos": conflitos,
        "total_preventivas": eventos.count(),
        "total_hh": round(total_hh, 2),
        "hh_por_oficina_lista": hh_por_oficina_lista,
        "total_hh_mes": [round(v, 1) for v in total_hh_mes],
        "total_hh_ano": round(sum(total_hh_mes), 1),
        "meses_label": _MESES_LABEL,
        "safra_mensal": cal["safra"],
        "cores_tipo": _COR_TIPO,
        "legenda_tipos": legenda_tipos,
    }
    return render(request, "plano/cronograma.html", contexto)


def agenda(request, org_slug: str):
    org = _get_org(org_slug)
    plano = plano_vigente(org)

    if plano is None:
        return render(
            request, "plano/agenda.html", {"org": org, "active_tab": "agenda", "plano": None}
        )

    eventos_qs = list(
        plano.eventos.select_related("ativo", "ativo__classe", "oficina", "responsavel").order_by(
            "data"
        )
    )
    if not eventos_qs:
        return render(
            request,
            "plano/agenda.html",
            {"org": org, "active_tab": "agenda", "plano": plano, "sem_eventos": True},
        )

    semanas, inicio = _semanas_do_plano(plano)

    vm_eventos = []
    for evento in eventos_qs:
        wi = _semana_idx(evento.data, inicio, len(semanas))
        equipe_padrao = f"Equipe {evento.oficina.nome}"
        mecanico = evento.responsavel.nome if evento.responsavel else equipe_padrao
        vm_eventos.append(
            {
                "data": evento.data,
                "ativo": evento.ativo.nome,
                "ativo_id": evento.ativo_id,
                "curto": _nome_curto(evento.ativo.nome),
                "classe": evento.ativo.classe.nome,
                "tipo": evento.tipo,
                "hh": float(evento.hh),
                "count": evento.count,
                "oficina": evento.oficina.nome,
                "mecanico": mecanico,
                "wi": wi,
                "safra": semanas[wi].safra,
            }
        )

    contagem_trimestre = [0, 0, 0, 0]
    for vm in vm_eventos:
        contagem_trimestre[min(3, vm["wi"] // 13)] += vm["count"]
    trimestre_padrao = contagem_trimestre.index(max(contagem_trimestre))

    try:
        q = int(request.GET.get("q", trimestre_padrao))
        if not 0 <= q <= 3:
            q = trimestre_padrao
    except ValueError:
        q = trimestre_padrao

    w_inicio, w_fim = q * 13, min(51, q * 13 + 12)
    d_inicio, d_fim = semanas[w_inicio].data, semanas[w_fim].fim
    mes_primeiro = d_inicio.replace(day=1)
    mes_ultimo = d_fim.replace(day=1)

    eventos_trimestre = [
        vm for vm in vm_eventos if mes_primeiro <= vm["data"].replace(day=1) <= mes_ultimo
    ]

    por_dia: dict[date, list] = {}
    for vm in eventos_trimestre:
        por_dia.setdefault(vm["data"], []).append(vm)

    n_prev = sum(vm["count"] for vm in eventos_trimestre)
    hh_total = round(sum(vm["hh"] for vm in eventos_trimestre), 2)
    n_ativos = len({vm["ativo_id"] for vm in eventos_trimestre})
    dia_top, dia_top_n = None, 0
    for dia, evs in por_dia.items():
        n = sum(vm["count"] for vm in evs)
        if n > dia_top_n:
            dia_top_n, dia_top = n, dia

    trimestres = []
    for qi in range(4):
        ws, we = qi * 13, min(51, qi * 13 + 12)
        trimestres.append(
            {
                "idx": qi,
                "label": f"{_MESES_LABEL[semanas[ws].data.month - 1]}–"
                f"{_MESES_LABEL[semanas[we].data.month - 1]}/{semanas[we].data:%y}",
                "ativo": qi == q,
            }
        )

    meses = []
    cursor = mes_primeiro
    while cursor <= mes_ultimo:
        meses.append(cursor)
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)

    meses_grid = []
    for mes in meses:
        _, n_dias = calendar.monthrange(mes.year, mes.month)
        primeiro_dow = (mes.weekday() + 1) % 7  # 0=Dom..6=Sab, igual ao Date.getDay() do JS
        dias_do_mes = [date(mes.year, mes.month, d) for d in range(1, n_dias + 1)]
        celulas = [None] * primeiro_dow + dias_do_mes
        while len(celulas) % 7:
            celulas.append(None)
        linhas = []
        for i in range(0, len(celulas), 7):
            linha = []
            for dia in celulas[i : i + 7]:
                if dia is None:
                    linha.append(None)
                    continue
                evs = por_dia.get(dia, [])
                linha.append(
                    {
                        "dia": dia,
                        "eventos": evs[:4],
                        "extra": max(0, len(evs) - 4),
                        "safra": any(vm["safra"] for vm in evs),
                        "fds": dia.weekday() >= 5,
                    }
                )
            linhas.append(linha)
        meses_grid.append({"mes": mes, "linhas": linhas})

    contexto = {
        "org": org,
        "active_tab": "agenda",
        "plano": plano,
        "trimestres": trimestres,
        "mes_primeiro": mes_primeiro,
        "mes_ultimo": mes_ultimo,
        "n_prev": n_prev,
        "hh_total": hh_total,
        "n_ativos": n_ativos,
        "dia_top": dia_top,
        "dia_top_n": dia_top_n,
        "meses_grid": meses_grid,
        "dow": _DOW,
        "eventos_trimestre": eventos_trimestre,
        "cores_tipo": _COR_TIPO,
        "legenda_tipos": [
            {"tipo": tipo, "cor": cor, "label": _LABEL_TIPO[tipo]}
            for tipo, cor in _COR_TIPO.items()
        ],
    }
    return render(request, "plano/agenda.html", contexto)


@require_POST
def recalcular(request, org_slug: str):
    org = _get_org(org_slug)
    task_recalcular_plano.defer(organizacao_id=org.pk)
    return render(request, "plano/_recalculo_enfileirado.html", {"org": org})
