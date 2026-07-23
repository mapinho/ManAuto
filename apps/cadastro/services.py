"""Conversao dos models Django (Ativo, ChecklistAtividade, Pessoa) para os
dataclasses puros do motor (apps/motor/tipos.py).

Usado pelas telas/tarefas que rodam o motor sobre os dados reais de uma
organizacao (Cronograma, Agenda, Disponibilidade — apps/plano/). A view/task
nunca reimplementa formula: so monta o input e chama o motor.

`.order_by("pk")` em todas as consultas e proposital, nao cosmetico: o
round-robin de mecanico (apps/motor/agenda.py:build_agenda_eventos) depende
da ORDEM da lista de pessoas — sem ordenacao explicita, o Postgres nao
garante a ordem das linhas, e o resultado (qual mecanico cai em qual evento)
deixa de ser deterministico entre execucoes.
"""

from __future__ import annotations

from apps.core.models import Organizacao
from apps.motor.tipos import Ativo as AtivoMotor
from apps.motor.tipos import ItemChecklist
from apps.motor.tipos import Pessoa as PessoaMotor

from .models import Ativo, ChecklistAtividade, Pessoa


def frota_motor(org: Organizacao) -> list[AtivoMotor]:
    return [
        AtivoMotor(
            id=ativo.pk,
            nome=ativo.nome,
            classe=ativo.classe.nome,
            status=ativo.status,
            t_gat=ativo.tipo_gatilho,
            uso=float(ativo.uso_atual),
            uso_med_safra=float(ativo.uso_sem_safra),
            uso_med_ent=float(ativo.uso_sem_entressafra),
            itv=float(ativo.intervalo),
        )
        for ativo in Ativo.objects.for_org(org).select_related("classe").order_by("pk")
    ]


def checklist_motor(org: Organizacao) -> list[ItemChecklist]:
    return [
        ItemChecklist(
            id=atividade.pk,
            tipo_prev=atividade.tipo_prev,
            classe=atividade.classe.nome,
            oficina=atividade.oficina.nome,
            atv=atividade.descricao,
            cargo=atividade.cargo,
            tipo_atividade=atividade.tipo_atividade,
            hh=float(atividade.hh),
        )
        for atividade in ChecklistAtividade.objects.for_org(org)
        .select_related("classe", "oficina")
        .order_by("pk")
    ]


def pessoas_motor(org: Organizacao) -> list[PessoaMotor]:
    return [
        PessoaMotor(
            id=pessoa.pk,
            nome=pessoa.nome,
            cargo=pessoa.cargo,
            oficina=pessoa.oficina.nome,
            turno=pessoa.turno,
            salario=float(pessoa.salario),
            encargos=float(pessoa.encargos_pct),
            status=pessoa.status,
        )
        for pessoa in Pessoa.objects.for_org(org).select_related("oficina").order_by("pk")
    ]
