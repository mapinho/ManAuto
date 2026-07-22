"""Tela de Premissas — modulo 1 (SPEC_Funcional.md SS2).

Indices e disponibilidade de MO por oficina (models.Oficina), calendario
(dias uteis/mes, safra, sazonal — ConjuntoPremissas.calendario JSONB) e
gatilhos de preventiva por classe (models.Gatilho). Edicao e feita campo a
campo via HTMX (cada input salva sozinho ao perder o foco/mudar) — os
identificadores do campo (campo/indice/tipo) viajam no corpo do POST via
`hx-vals`, nunca na URL (query string cai em request.GET, nao em
request.POST).

Nenhum calculo mora aqui — a tela so le/grava cadastro e premissas; quem
calcula e o motor (apps/motor/), chamado pelas telas de Cronograma/Agenda/
Disponibilidade (proximas telas do roadmap R1).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.cadastro.models import ClasseAtivo, Gatilho, Oficina, TipoPreventiva, Unidade
from apps.core.models import Organizacao
from apps.motor.heranca import HERANCA_PADRAO
from apps.motor.horas import calc_horas_liquidas
from apps.motor.tipos import DispOficina

from .models import ConjuntoPremissas

_DISP_PADRAO = {
    "h_brutas": 8.8,
    "almoco": 1.0,
    "cafe": 0.17,
    "prod": 80,
    "abs": 5,
    "ferias": 8.33,
    "trein": 8,
    "abr_os": 0.17,
}

# (rotulo, unidade de medida, nome do campo, passo do input)
_LINHAS_INDICES = (
    ("% Manutenções Preventivas", "%", "prev_pct", "5"),
    ("% Corretivas Esperadas", "%", "corr_pct", "5"),
    ("Fator Deflator Corretivas (redução a.a.)", "% a.a.", "deflator_pct", "0.5"),
    ("% Serviços por Terceiros", "%", "terceiros_pct", "5"),
)
_LINHAS_DISP = (
    ("Horas brutas / dia", "HH", "h_brutas", "0.1"),
    ("Desconto almoço", "HH", "almoco", "0.05"),
    ("Desconto café", "HH", "cafe", "0.05"),
    ("Produtividade", "%", "prod", "1"),
    ("Absenteísmo", "%", "abs", "1"),
    ("Férias (ao ano)", "%", "ferias", "0.5"),
    ("Treinamentos e DDS", "h/ano", "trein", "1"),
    ("Abertura/Fechamento de OS", "HH/dia", "abr_os", "0.05"),
)

MESES = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)

_CALENDARIO_PADRAO = {
    "dias_uteis": [22] * 12,
    "safra": [False] * 12,
    "sazonal": [1.0] * 12,
    "inicio_safra": "2026-04-01",
    "fim_safra": "2026-11-30",
    "heranca": {tipo: list(itens) for tipo, itens in HERANCA_PADRAO.items()},
}

_CAMPOS_INDICES = ("prev_pct", "corr_pct", "deflator_pct", "terceiros_pct")
_CAMPOS_DISP = ("h_brutas", "almoco", "cafe", "prod", "abs", "ferias", "trein", "abr_os")


def _get_org(org_slug: str) -> Organizacao:
    return get_object_or_404(Organizacao, slug=org_slug)


def _conjunto_vigente(org: Organizacao, *, travar: bool = False) -> ConjuntoPremissas:
    """`travar=True` bloqueia a linha (SELECT ... FOR UPDATE) — exige rodar dentro
    de `transaction.atomic()`. Necessario em toda leitura-e-gravacao do JSON
    `calendario`: sem lock, dois POSTs quase simultaneos (usuario tabulando por
    varias celulas do calendario) leem o mesmo JSON antes de qualquer um salvar,
    e o segundo `save()` sobrescreve a mudanca do primeiro (visto na pratica:
    8 campos de disponibilidade enviados em paralelo perderam 1 atualizacao).
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
            calendario=dict(_CALENDARIO_PADRAO),
        )
    return conjunto


def _calendario(conjunto: ConjuntoPremissas) -> dict:
    return {**_CALENDARIO_PADRAO, **conjunto.calendario}


def _horas_liquidas(oficina: Oficina):
    """Chama o motor (apps/motor/horas.py) — a view nunca reimplementa a formula."""
    dados = {**_DISP_PADRAO, **oficina.disp_mo}
    disp = DispOficina(
        h_brutas=float(dados["h_brutas"]),
        almoco=float(dados["almoco"]),
        cafe=float(dados["cafe"]),
        prod=float(dados["prod"]),
        abs_=float(dados["abs"]),
        ferias=float(dados["ferias"]),
        trein=float(dados["trein"]),
        abr_os=float(dados["abr_os"]),
    )
    return calc_horas_liquidas(disp)


def _parse_decimal(valor: str) -> Decimal:
    texto = (valor or "").strip().replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValidationError(f"valor inválido: {valor!r}") from exc


def _campo_numero(request, *, valor, post_url: str, step: str, hx_vals: str | None = None):
    return render(
        request,
        "_campo_numero.html",
        {"valor": valor, "post_url": post_url, "step": step, "hx_vals": hx_vals},
    )


def index(request, org_slug: str):
    org = _get_org(org_slug)
    oficinas = list(Oficina.objects.for_org(org).order_by("nome"))
    classes = list(ClasseAtivo.objects.for_org(org).prefetch_related("gatilhos").order_by("nome"))
    conjunto = _conjunto_vigente(org)
    calendario = _calendario(conjunto)
    dias_medios = sum(calendario["dias_uteis"]) / 12

    for oficina in oficinas:
        horas = _horas_liquidas(oficina)
        oficina.horas_liquidas = horas
        oficina.horas_liquidas_mes = round(horas.liquidas * dias_medios, 2)

    for classe in classes:
        por_tipo = {g.tipo: g for g in classe.gatilhos.all()}
        classe.gatilho_por_tipo = [(tp, por_tipo.get(tp.value)) for tp in TipoPreventiva]

    linhas_indices = [
        {
            "label": label,
            "unidade": unidade,
            "campo": campo,
            "passo": passo,
            "valores": [(of, getattr(of, campo)) for of in oficinas],
        }
        for label, unidade, campo, passo in _LINHAS_INDICES
    ]
    linhas_disp = [
        {
            "label": label,
            "unidade": unidade,
            "campo": campo,
            "passo": passo,
            "valores": [(of, of.disp_mo.get(campo, _DISP_PADRAO.get(campo, 0))) for of in oficinas],
        }
        for label, unidade, campo, passo in _LINHAS_DISP
    ]
    linhas_calendario_mensal = [
        {
            "label": "Dias úteis no mês",
            "campo": "dias_uteis",
            "passo": "1",
            "valores": list(enumerate(calendario["dias_uteis"])),
        },
        {
            "label": "Fator sazonalidade corretiva",
            "campo": "sazonal",
            "passo": "0.1",
            "valores": list(enumerate(calendario["sazonal"])),
        },
    ]

    contexto = {
        "org": org,
        "active_tab": "premissas",
        "oficinas": oficinas,
        "classes": classes,
        "conjunto": conjunto,
        "calendario": calendario,
        "linhas_indices": linhas_indices,
        "linhas_disp": linhas_disp,
        "linhas_calendario_mensal": linhas_calendario_mensal,
        "safra_mensal": list(enumerate(calendario["safra"])),
        "safra_url": reverse("premissas:alternar_safra_mes", args=[org.slug]),
        "meses": list(enumerate(MESES)),
        "tipos_preventiva": list(TipoPreventiva),
        "unidades": list(Unidade),
        "heranca": calendario.get("heranca") or _CALENDARIO_PADRAO["heranca"],
    }
    return render(request, "premissas/index.html", contexto)


@require_POST
def atualizar_indices(request, org_slug: str, oficina_id: int):
    org = _get_org(org_slug)
    oficina = get_object_or_404(Oficina, organizacao=org, pk=oficina_id)
    campo = request.POST.get("campo")
    if campo not in _CAMPOS_INDICES:
        return HttpResponse("campo inválido", status=400)
    try:
        valor = _parse_decimal(request.POST.get("valor"))
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)
    setattr(oficina, campo, valor)
    oficina.save(update_fields=[campo])
    return _campo_numero(
        request,
        valor=valor,
        post_url=reverse("premissas:atualizar_indices", args=[org.slug, oficina.pk]),
        step="0.5" if campo == "deflator_pct" else "5",
        hx_vals=f'{{"campo": "{campo}"}}',
    )


@require_POST
def atualizar_disp(request, org_slug: str, oficina_id: int):
    org = _get_org(org_slug)
    campo = request.POST.get("campo")
    if campo not in _CAMPOS_DISP:
        return HttpResponse("campo inválido", status=400)
    try:
        valor = _parse_decimal(request.POST.get("valor"))
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)

    # select_for_update(): sem lock, dois POSTs quase simultaneos para o mesmo
    # oficina (usuario tabulando por varios campos de disponibilidade) leem o
    # mesmo disp_mo antes de qualquer um salvar, e o segundo save() apaga a
    # mudanca do primeiro — reproduzido na pratica (8 campos em paralelo
    # perderam 1 atualizacao).
    with transaction.atomic():
        oficina = get_object_or_404(
            Oficina.objects.select_for_update(), organizacao=org, pk=oficina_id
        )
        disp_mo = dict(oficina.disp_mo)
        disp_mo[campo] = float(valor)
        oficina.disp_mo = disp_mo
        oficina.save(update_fields=["disp_mo"])

    return _campo_numero(
        request,
        valor=valor,
        post_url=reverse("premissas:atualizar_disp", args=[org.slug, oficina.pk]),
        step="0.05",
        hx_vals=f'{{"campo": "{campo}"}}',
    )


@require_POST
def atualizar_calendario_mes(request, org_slug: str):
    org = _get_org(org_slug)
    campo = request.POST.get("campo")
    if campo not in ("dias_uteis", "sazonal"):
        return HttpResponse("campo inválido", status=400)
    try:
        indice = int(request.POST.get("indice", ""))
        assert 0 <= indice <= 11
    except ValueError, AssertionError:
        return HttpResponse("índice inválido", status=400)
    try:
        valor = _parse_decimal(request.POST.get("valor"))
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)

    with transaction.atomic():
        conjunto = _conjunto_vigente(org, travar=True)
        calendario = _calendario(conjunto)
        lista = list(calendario[campo])
        lista[indice] = int(valor) if campo == "dias_uteis" else float(valor)
        calendario[campo] = lista
        conjunto.calendario = calendario
        conjunto.save(update_fields=["calendario"])

    return _campo_numero(
        request,
        valor=lista[indice],
        post_url=reverse("premissas:atualizar_calendario_mes", args=[org.slug]),
        step="1" if campo == "dias_uteis" else "0.1",
        hx_vals=f'{{"campo": "{campo}", "indice": {indice}}}',
    )


@require_POST
def alternar_safra_mes(request, org_slug: str):
    org = _get_org(org_slug)
    try:
        indice = int(request.POST.get("indice", ""))
        assert 0 <= indice <= 11
    except ValueError, AssertionError:
        return HttpResponse("índice inválido", status=400)

    with transaction.atomic():
        conjunto = _conjunto_vigente(org, travar=True)
        calendario = _calendario(conjunto)
        safra = list(calendario["safra"])
        safra[indice] = not safra[indice]
        calendario["safra"] = safra
        conjunto.calendario = calendario
        conjunto.save(update_fields=["calendario"])

    return render(
        request,
        "premissas/_botao_safra.html",
        {
            "post_url": reverse("premissas:alternar_safra_mes", args=[org.slug]),
            "indice": indice,
            "safra": safra[indice],
        },
    )


@require_POST
def atualizar_datas_safra(request, org_slug: str):
    org = _get_org(org_slug)
    with transaction.atomic():
        conjunto = _conjunto_vigente(org, travar=True)
        calendario = _calendario(conjunto)
        inicio = request.POST.get("inicio_safra") or calendario["inicio_safra"]
        fim = request.POST.get("fim_safra") or calendario["fim_safra"]
        calendario["inicio_safra"] = inicio
        calendario["fim_safra"] = fim
        conjunto.calendario = calendario
        conjunto.save(update_fields=["calendario"])
    return HttpResponse('<span class="cv" style="font-size:10px">✓ salvo</span>')


@require_POST
def atualizar_gatilho(request, org_slug: str, classe_id: int):
    org = _get_org(org_slug)
    classe = get_object_or_404(ClasseAtivo, organizacao=org, pk=classe_id)
    tipo = request.POST.get("tipo")
    if tipo not in TipoPreventiva.values:
        return HttpResponse("tipo inválido", status=400)
    intervalo_raw = (request.POST.get("intervalo") or "").strip()
    hx_vals = f'{{"tipo": "{tipo}"}}'
    post_url = reverse("premissas:atualizar_gatilho", args=[org.slug, classe.pk])

    if not intervalo_raw:
        Gatilho.objects.filter(classe=classe, tipo=tipo).delete()
        return _campo_numero(request, valor="", post_url=post_url, step="50", hx_vals=hx_vals)

    try:
        valor = _parse_decimal(intervalo_raw)
    except ValidationError as exc:
        return HttpResponse(str(exc), status=400)

    ordem = TipoPreventiva.values.index(tipo)
    Gatilho.objects.update_or_create(
        organizacao=org,
        classe=classe,
        tipo=tipo,
        defaults={"intervalo": valor, "ordem": ordem},
    )
    return _campo_numero(request, valor=valor, post_url=post_url, step="50", hx_vals=hx_vals)


@require_POST
def atualizar_classe_unidade(request, org_slug: str, classe_id: int):
    org = _get_org(org_slug)
    classe = get_object_or_404(ClasseAtivo, organizacao=org, pk=classe_id)
    unidade = request.POST.get("unidade")
    if unidade not in Unidade.values:
        return HttpResponse("unidade inválida", status=400)
    classe.unidade = unidade
    classe.save(update_fields=["unidade"])
    return HttpResponse("")
