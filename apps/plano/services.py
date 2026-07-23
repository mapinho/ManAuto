"""Recalculo do plano de preventivas — orquestra o motor sobre o cadastro
vigente e persiste o resultado (PlanoAnual + EventoPreventiva).

NUNCA roda no request (CLAUDE.md: jobs longos sempre via Procrastinate): a
tela de Cronograma dispara isto via `apps/plano/tasks.py`, e `manage.py
recalcula_plano` roda a mesma funcao de forma sincrona para uso via CLI/ops
— mesmo padrao ja estabelecido pelos importadores (apps/importacao/tasks.py).

A oficina e resolvida por nome (unique_together organizacao+nome em
Oficina). O ativo precisa ser resolvido por id (Ativo.nome NAO e unico) —
por isso o motor carrega `EventoAgenda.ativo_id` (apps/motor/tipos.py).
O responsavel (Pessoa) e resolvido por (oficina, nome) em melhor esforco:
quando o motor cai no fallback "Equipe {oficina}" (nenhuma pessoa ativa),
nao ha correspondencia e `responsavel` fica None, corretamente.
"""

from __future__ import annotations

from django.db import transaction

from apps.cadastro.models import Ativo, Oficina, Pessoa
from apps.cadastro.services import checklist_motor, frota_motor, pessoas_motor
from apps.core.models import Organizacao
from apps.motor.agenda import build_agenda_eventos
from apps.motor.cronograma import calc_cronograma_mensal, calc_cronograma_semanal
from apps.motor.plano import calc_plan_prev
from apps.premissas.services import conjunto_vigente, montar_premissas

from .models import EventoPreventiva, PlanoAnual


def recalcular_plano(organizacao: Organizacao) -> PlanoAnual:
    premissas = montar_premissas(organizacao)
    frota = frota_motor(organizacao)
    checklist = checklist_motor(organizacao)
    pessoas = pessoas_motor(organizacao)

    eventos_motor = build_agenda_eventos(frota, premissas, checklist, pessoas)

    grid_semanal, _ = calc_cronograma_semanal(frota, premissas, checklist)
    grid_mensal = calc_cronograma_mensal(grid_semanal, frota)
    hh_prev_por_oficina = calc_plan_prev(grid_mensal, frota, checklist, premissas)

    ativos_por_id = {a.pk: a for a in Ativo.objects.for_org(organizacao)}
    oficinas_por_nome = {of.nome: of for of in Oficina.objects.for_org(organizacao)}
    pessoas_por_oficina_nome = {
        (p.oficina_id, p.nome): p
        for p in Pessoa.objects.for_org(organizacao).filter(status=Pessoa.Status.ATIVO)
    }

    with transaction.atomic():
        conjunto = conjunto_vigente(organizacao)
        plano = PlanoAnual.objects.create(
            organizacao=organizacao,
            conjunto_premissas=conjunto,
            hh_prev_por_oficina=hh_prev_por_oficina,
        )

        linhas = []
        for evento in eventos_motor:
            oficina = oficinas_por_nome.get(evento.oficina)
            if oficina is None:
                continue
            responsavel = pessoas_por_oficina_nome.get((oficina.pk, evento.mecanico))
            linhas.append(
                EventoPreventiva(
                    organizacao=organizacao,
                    plano_anual=plano,
                    data=evento.data,
                    ativo=ativos_por_id[evento.ativo_id],
                    tipo=evento.tipo,
                    hh=evento.hh,
                    count=evento.count,
                    oficina=oficina,
                    responsavel=responsavel,
                )
            )
        EventoPreventiva.objects.bulk_create(linhas)

    return plano


def plano_vigente(organizacao: Organizacao) -> PlanoAnual | None:
    return PlanoAnual.objects.for_org(organizacao).order_by("-criado_em").first()
