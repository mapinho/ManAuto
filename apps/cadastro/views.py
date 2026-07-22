"""Telas de Frota e Pessoas — modulos 2 e 3 do roadmap R1 (SPEC_Tecnica_Ambiente.md SS6).

Frota: cadastro central de ativos (models.Ativo). Pessoas: banco de mao de
obra (models.Pessoa), com Custo/HH calculado pelo motor (apps/motor/horas.py)
usando o calendario e a disponibilidade vigentes (apps/premissas/services.py)
— a view nunca reimplementa a formula.

Edicao campo a campo via HTMX em ambas, mesmo padrao da tela de Premissas
(apps/premissas/views.py): identificadores de campo viajam no corpo do POST
via `hx-vals`, nunca na query string.

"Próxima preventiva" (Frota) e calculada pelo motor
(apps/motor/proxima_preventiva.py) a partir do uso acumulado e do intervalo.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.models import Organizacao
from apps.motor.horas import calc_custo_pessoa
from apps.motor.proxima_preventiva import calcular_proxima_preventiva
from apps.motor.tipos import Pessoa as PessoaMotor
from apps.premissas import services as premissas_services

from .models import Ativo, ClasseAtivo, Oficina, Pessoa, Unidade

_POR_PAGINA = 50

_CAMPOS_NUMERICOS = {
    "uso_atual": "10",
    "uso_sem_safra": "5",
    "uso_sem_entressafra": "5",
    "intervalo": "50",
}

_CAMPOS_SELECT = {
    "status": Ativo.Status.values,
    "tipo_gatilho": Unidade.values,
}


def _get_org(org_slug: str) -> Organizacao:
    return get_object_or_404(Organizacao, slug=org_slug)


def _com_proxima_preventiva(ativo: Ativo) -> Ativo:
    uso_medio = float(ativo.uso_sem_safra + ativo.uso_sem_entressafra) / 2
    ativo.proxima_preventiva = calcular_proxima_preventiva(
        uso=float(ativo.uso_atual),
        intervalo=float(ativo.intervalo),
        uso_medio_mensal=uso_medio,
    )
    return ativo


def _campo_numero(request, *, valor, post_url: str, step: str, hx_vals: str | None = None):
    return render(
        request,
        "_campo_numero.html",
        {"valor": valor, "post_url": post_url, "step": step, "hx_vals": hx_vals},
    )


def _parse_decimal(valor: str) -> Decimal:
    texto = (valor or "").strip().replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValidationError(f"valor inválido: {valor!r}") from exc


def frota(request, org_slug: str):
    org = _get_org(org_slug)
    ativos = Ativo.objects.for_org(org).select_related("classe", "oficina").order_by("nome")

    classe_id = request.GET.get("classe") or ""
    status = request.GET.get("status") or ""
    oficina_id = request.GET.get("oficina") or ""
    busca = request.GET.get("busca") or ""
    if classe_id:
        ativos = ativos.filter(classe_id=classe_id)
    if status:
        ativos = ativos.filter(status=status)
    if oficina_id:
        ativos = ativos.filter(oficina_id=oficina_id)
    if busca:
        ativos = ativos.filter(nome__icontains=busca)

    paginador = Paginator(ativos, _POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("page"))
    for ativo in pagina.object_list:
        _com_proxima_preventiva(ativo)

    classes = list(ClasseAtivo.objects.for_org(org).order_by("nome"))
    oficinas = list(Oficina.objects.for_org(org).order_by("nome"))

    total_ativos = Ativo.objects.for_org(org).count()
    ativos_ativos = Ativo.objects.for_org(org).filter(status=Ativo.Status.ATIVO)
    kpis_classe = [
        {"nome": classe.nome, "total": ativos_ativos.filter(classe=classe).count()}
        for classe in classes
    ]

    query_sem_page = request.GET.copy()
    query_sem_page.pop("page", None)

    contexto = {
        "org": org,
        "active_tab": "frota",
        "pagina": pagina,
        "classes": classes,
        "oficinas": oficinas,
        "status_opcoes": list(Ativo.Status),
        "unidade_opcoes": list(Unidade),
        "filtro_classe": classe_id,
        "filtro_status": status,
        "filtro_oficina": oficina_id,
        "filtro_busca": busca,
        "total_ativos": total_ativos,
        "total_ativos_ativos": ativos_ativos.count(),
        "kpis_classe": kpis_classe,
        "query_sem_page": query_sem_page.urlencode(),
    }
    return render(request, "cadastro/frota.html", contexto)


@require_POST
def atualizar_numero(request, org_slug: str, ativo_id: int):
    org = _get_org(org_slug)
    ativo = get_object_or_404(Ativo, organizacao=org, pk=ativo_id)
    campo = request.POST.get("campo")
    if campo not in _CAMPOS_NUMERICOS:
        return HttpResponse("campo inválido", status=400)
    try:
        valor = _parse_decimal(request.POST.get("valor"))
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)

    setattr(ativo, campo, valor)
    ativo.save(update_fields=[campo])
    return _campo_numero(
        request,
        valor=valor,
        post_url=reverse("cadastro:atualizar_numero", args=[org.slug, ativo.pk]),
        step=_CAMPOS_NUMERICOS[campo],
        hx_vals=f'{{"campo": "{campo}"}}',
    )


@require_POST
def atualizar_select(request, org_slug: str, ativo_id: int):
    org = _get_org(org_slug)
    ativo = get_object_or_404(Ativo, organizacao=org, pk=ativo_id)
    campo = request.POST.get("campo")
    valores_validos = _CAMPOS_SELECT.get(campo)
    if valores_validos is None:
        return HttpResponse("campo inválido", status=400)
    valor = request.POST.get("valor")
    if valor not in valores_validos:
        return HttpResponse("valor inválido", status=400)
    setattr(ativo, campo, valor)
    ativo.save(update_fields=[campo])
    return HttpResponse("")


@require_POST
def atualizar_classe(request, org_slug: str, ativo_id: int):
    org = _get_org(org_slug)
    ativo = get_object_or_404(Ativo, organizacao=org, pk=ativo_id)
    classe = get_object_or_404(ClasseAtivo, organizacao=org, pk=request.POST.get("classe_id"))
    ativo.classe = classe
    ativo.save(update_fields=["classe"])
    return HttpResponse("")


@require_POST
def atualizar_oficina(request, org_slug: str, ativo_id: int):
    org = _get_org(org_slug)
    ativo = get_object_or_404(Ativo, organizacao=org, pk=ativo_id)
    oficina_id = request.POST.get("oficina_id") or None
    oficina = None
    if oficina_id:
        oficina = get_object_or_404(Oficina, organizacao=org, pk=oficina_id)
    ativo.oficina = oficina
    ativo.save(update_fields=["oficina"])
    return HttpResponse("")


@require_POST
def atualizar_garantia(request, org_slug: str, ativo_id: int):
    org = _get_org(org_slug)
    ativo = get_object_or_404(Ativo, organizacao=org, pk=ativo_id)
    ativo.garantia = request.POST.get("valor") == "true"
    ativo.save(update_fields=["garantia"])
    return HttpResponse("")


_PESSOAS_CAMPOS_NUMERICOS = {
    "salario": "100",
    "encargos_pct": "1",
}

_PESSOAS_CAMPOS_SELECT = {
    "turno": Pessoa.Turno.values,
    "status": Pessoa.Status.values,
}


def _com_custo(pessoa: Pessoa, dias_uteis: tuple[float, ...]) -> Pessoa:
    motor_pessoa = PessoaMotor(
        id=pessoa.pk,
        nome=pessoa.nome,
        cargo=pessoa.cargo,
        oficina=pessoa.oficina.nome,
        turno=pessoa.turno,
        salario=float(pessoa.salario),
        encargos=float(pessoa.encargos_pct),
        status=pessoa.status,
    )
    disp = premissas_services.disp_oficina(pessoa.oficina)
    pessoa.custo = calc_custo_pessoa(motor_pessoa, disp, dias_uteis)
    return pessoa


def pessoas(request, org_slug: str):
    org = _get_org(org_slug)
    conjunto = premissas_services.conjunto_vigente(org)
    calendario = premissas_services.calendario(conjunto)
    dias_uteis = tuple(calendario["dias_uteis"])
    dias_medios = sum(dias_uteis) / 12

    pessoas_qs = Pessoa.objects.for_org(org).select_related("oficina").order_by("nome")

    oficina_id = request.GET.get("oficina") or ""
    turno = request.GET.get("turno") or ""
    status = request.GET.get("status") or ""
    busca = request.GET.get("busca") or ""
    if oficina_id:
        pessoas_qs = pessoas_qs.filter(oficina_id=oficina_id)
    if turno:
        pessoas_qs = pessoas_qs.filter(turno=turno)
    if status:
        pessoas_qs = pessoas_qs.filter(status=status)
    if busca:
        pessoas_qs = pessoas_qs.filter(nome__icontains=busca)

    paginador = Paginator(pessoas_qs, _POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("page"))
    for pessoa in pagina.object_list:
        _com_custo(pessoa, dias_uteis)

    oficinas = list(Oficina.objects.for_org(org).order_by("nome"))
    ativas = Pessoa.objects.for_org(org).filter(status=Pessoa.Status.ATIVO).select_related(
        "oficina"
    )

    cards_oficina = []
    resumo_oficina = []
    for oficina in oficinas:
        ps_of = list(ativas.filter(oficina=oficina))
        if not ps_of:
            continue
        liquidas = premissas_services.horas_liquidas(oficina).liquidas
        custo_of = sum(float(_com_custo(p, dias_uteis).custo.custo_mensal) for p in ps_of)
        cards_oficina.append({"nome": oficina.nome, "qtd": len(ps_of), "liquidas": liquidas})
        resumo_oficina.append(
            {
                "nome": oficina.nome,
                "qtd": len(ps_of),
                "custo_mes": round(custo_of, 2),
                "hh_mes": round(len(ps_of) * dias_medios * liquidas, 2),
            }
        )

    custo_total_mes = sum(item["custo_mes"] for item in resumo_oficina)

    query_sem_page = request.GET.copy()
    query_sem_page.pop("page", None)

    contexto = {
        "org": org,
        "active_tab": "pessoas",
        "pagina": pagina,
        "oficinas": oficinas,
        "turno_opcoes": list(Pessoa.Turno),
        "status_opcoes": list(Pessoa.Status),
        "filtro_oficina": oficina_id,
        "filtro_turno": turno,
        "filtro_status": status,
        "filtro_busca": busca,
        "total_ativos": ativas.count(),
        "custo_total_mes": round(custo_total_mes, 2),
        "custo_total_ano": round(custo_total_mes * 12, 2),
        "cards_oficina": cards_oficina,
        "resumo_oficina": resumo_oficina,
        "query_sem_page": query_sem_page.urlencode(),
    }
    return render(request, "cadastro/pessoas.html", contexto)


@require_POST
def pessoas_atualizar_numero(request, org_slug: str, pessoa_id: int):
    org = _get_org(org_slug)
    pessoa = get_object_or_404(Pessoa, organizacao=org, pk=pessoa_id)
    campo = request.POST.get("campo")
    if campo not in _PESSOAS_CAMPOS_NUMERICOS:
        return HttpResponse("campo inválido", status=400)
    try:
        valor = _parse_decimal(request.POST.get("valor"))
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)

    setattr(pessoa, campo, valor)
    pessoa.save(update_fields=[campo])
    return _campo_numero(
        request,
        valor=valor,
        post_url=reverse("cadastro:pessoas_atualizar_numero", args=[org.slug, pessoa.pk]),
        step=_PESSOAS_CAMPOS_NUMERICOS[campo],
        hx_vals=f'{{"campo": "{campo}"}}',
    )


@require_POST
def pessoas_atualizar_select(request, org_slug: str, pessoa_id: int):
    org = _get_org(org_slug)
    pessoa = get_object_or_404(Pessoa, organizacao=org, pk=pessoa_id)
    campo = request.POST.get("campo")
    valores_validos = _PESSOAS_CAMPOS_SELECT.get(campo)
    if valores_validos is None:
        return HttpResponse("campo inválido", status=400)
    valor = request.POST.get("valor")
    if valor not in valores_validos:
        return HttpResponse("valor inválido", status=400)
    setattr(pessoa, campo, valor)
    pessoa.save(update_fields=[campo])
    return HttpResponse("")


@require_POST
def pessoas_atualizar_oficina(request, org_slug: str, pessoa_id: int):
    org = _get_org(org_slug)
    pessoa = get_object_or_404(Pessoa, organizacao=org, pk=pessoa_id)
    oficina = get_object_or_404(Oficina, organizacao=org, pk=request.POST.get("oficina_id"))
    pessoa.oficina = oficina
    pessoa.save(update_fields=["oficina"])
    return HttpResponse("")
