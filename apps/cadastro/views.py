"""Tela de Frota — modulo 2 do roadmap R1 (SPEC_Tecnica_Ambiente.md SS6).

Cadastro central de ativos (models.Ativo). Edicao campo a campo via HTMX,
mesmo padrao da tela de Premissas (apps/premissas/views.py): identificadores
de campo viajam no corpo do POST via `hx-vals`, nunca na query string.

"Próxima preventiva" e calculada pelo motor (apps/motor/proxima_preventiva.py)
a partir do uso acumulado e do intervalo — a view nunca reimplementa a conta.
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
from apps.motor.proxima_preventiva import calcular_proxima_preventiva

from .models import Ativo, ClasseAtivo, Oficina, Unidade

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


def index(request, org_slug: str):
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
