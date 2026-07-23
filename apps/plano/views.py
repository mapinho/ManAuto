"""Tela de Cronograma — modulo 5 do roadmap R1 (SPEC_Tecnica_Ambiente.md SS6).

Le o `PlanoAnual` mais recente (persistido por `apps/plano/services.py`) e
monta a grade semanal (ativo x 52 semanas) e o resumo mensal de HH por
oficina — nunca roda o motor no request (CLAUDE.md): "Recalcular Plano"
enfileira `apps/plano/tasks.py` via Procrastinate.
"""

from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.cadastro.models import Ativo, ClasseAtivo, Oficina, Pessoa
from apps.core.models import Organizacao
from apps.motor.semanas import gerar_semanas
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
    inicio_safra = date.fromisoformat(cal["inicio_safra"])
    fim_safra = date.fromisoformat(cal["fim_safra"])
    semanas = gerar_semanas(inicio_safra, fim_safra)
    inicio = semanas[0].data

    eventos = (
        plano.eventos.select_related("ativo", "ativo__classe")
        .order_by("ativo__classe__nome", "ativo__nome", "data")
    )

    grid: dict[int, dict[int, dict]] = {}
    hh_por_semana = [0.0] * len(semanas)
    total_hh = 0.0
    for evento in eventos:
        idx = max(0, min(len(semanas) - 1, (evento.data - inicio).days // 7))
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
        "meses_label": (
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ),
        "safra_mensal": cal["safra"],
        "cores_tipo": _COR_TIPO,
        "legenda_tipos": legenda_tipos,
    }
    return render(request, "plano/cronograma.html", contexto)


@require_POST
def recalcular(request, org_slug: str):
    org = _get_org(org_slug)
    task_recalcular_plano.defer(organizacao_id=org.pk)
    return render(request, "plano/_recalculo_enfileirado.html", {"org": org})
