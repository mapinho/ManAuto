"""Popula o cadastro (models Django) a partir dos dataclasses puros do motor.

Usado pelos comandos `seed_demo` e `seed_petribu` — a fonte dos dados e
sempre `apps/motor/fixtures/dados_*.py` (os mesmos dados dos fixtures de
regressao do motor), para que o banco semeado e os testes nunca divirjam.

Reseed e idempotente: a organizacao (por slug) e reaproveitada e todo o
cadastro anterior dela e apagado antes de recriar.
"""

from __future__ import annotations

from django.db import transaction

from apps.cadastro.models import (
    AtividadeMaterial,
    Ativo,
    ChecklistAtividade,
    ClasseAtivo,
    Gatilho,
    ItemMaterial,
    Oficina,
    Pessoa,
)
from apps.core.models import Organizacao
from apps.motor.tipos import Ativo as AtivoMotor
from apps.motor.tipos import ItemChecklist, Premissas
from apps.motor.tipos import Pessoa as PessoaMotor
from apps.premissas.models import ConjuntoPremissas

# ordem de delecao: filhos que protegem (PROTECT) seus pais entram antes.
_MODELOS_PARA_LIMPAR = (
    AtividadeMaterial,
    ChecklistAtividade,
    ItemMaterial,
    Ativo,
    Gatilho,
    ClasseAtivo,
    Pessoa,
    Oficina,
    ConjuntoPremissas,
)


@transaction.atomic
def semear_organizacao(
    *,
    slug: str,
    nome: str,
    premissas: Premissas,
    frota: list[AtivoMotor],
    pessoas: list[PessoaMotor],
    checklist: list[ItemChecklist],
) -> Organizacao:
    org, _ = Organizacao.objects.get_or_create(slug=slug, defaults={"nome": nome})
    if org.nome != nome:
        org.nome = nome
        org.save(update_fields=["nome"])

    for modelo in _MODELOS_PARA_LIMPAR:
        modelo.objects.for_org(org).delete()

    oficinas_db = {}
    for nome_of in premissas.oficinas:
        idx = premissas.indices[nome_of]
        disp = premissas.disp[nome_of]
        oficinas_db[nome_of] = Oficina.objects.create(
            organizacao=org,
            nome=nome_of,
            prev_pct=idx.prev,
            corr_pct=idx.corr,
            deflator_pct=idx.deflator,
            terceiros_pct=idx.terceiros,
            disp_mo={
                "h_brutas": disp.h_brutas,
                "almoco": disp.almoco,
                "cafe": disp.cafe,
                "prod": disp.prod,
                "abs": disp.abs_,
                "ferias": disp.ferias,
                "trein": disp.trein,
                "abr_os": disp.abr_os,
            },
        )

    classes_db = {}
    for nome_classe, gatilhos_classe in premissas.gatilhos.items():
        classe = ClasseAtivo.objects.create(
            organizacao=org, nome=nome_classe, unidade=gatilhos_classe.tipo_medida
        )
        classes_db[nome_classe] = classe
        for ordem, itv in enumerate(gatilhos_classe.itvs):
            Gatilho.objects.create(
                organizacao=org, classe=classe, tipo=itv.tipo, intervalo=itv.valor, ordem=ordem
            )

    ConjuntoPremissas.objects.create(
        organizacao=org,
        versao=1,
        vigente=True,
        calendario={
            "dias_uteis": list(premissas.dias_uteis),
            "safra": list(premissas.safra),
            "sazonal": list(premissas.sazonal),
            "inicio_safra": premissas.inicio_safra.isoformat(),
            "fim_safra": premissas.fim_safra.isoformat(),
            "heranca": {tipo: list(v) for tipo, v in premissas.heranca.items()},
        },
    )

    for ativo in frota:
        classe = classes_db.get(ativo.classe)
        if classe is None:
            continue
        Ativo.objects.create(
            organizacao=org,
            nome=ativo.nome,
            classe=classe,
            status=ativo.status,
            tipo_gatilho=ativo.t_gat,
            uso_atual=ativo.uso,
            uso_sem_safra=ativo.uso_med_safra,
            uso_sem_entressafra=ativo.uso_med_ent,
            intervalo=ativo.itv,
        )

    pessoas_db = {}
    for pessoa in pessoas:
        oficina = oficinas_db.get(pessoa.oficina)
        if oficina is None:
            continue
        pessoas_db[pessoa.id] = Pessoa.objects.create(
            organizacao=org,
            nome=pessoa.nome,
            oficina=oficina,
            cargo=pessoa.cargo,
            turno=pessoa.turno,
            salario=pessoa.salario,
            encargos_pct=pessoa.encargos,
            status=pessoa.status,
        )

    itens_material: dict[tuple[str, str], ItemMaterial] = {}

    def _item_material(descricao: str, tipo: str, unidade: str) -> ItemMaterial | None:
        if not descricao:
            return None
        chave = (descricao, tipo)
        if chave not in itens_material:
            itens_material[chave] = ItemMaterial.objects.create(
                organizacao=org, descricao=descricao, tipo=tipo, unidade=unidade or "un"
            )
        return itens_material[chave]

    for item_chk in checklist:
        classe = classes_db.get(item_chk.classe)
        oficina = oficinas_db.get(item_chk.oficina)
        if classe is None or oficina is None:
            continue
        atividade = ChecklistAtividade.objects.create(
            organizacao=org,
            classe=classe,
            tipo_prev=item_chk.tipo_prev,
            oficina=oficina,
            descricao=item_chk.atv,
            cargo=item_chk.cargo,
            tipo_atividade=item_chk.tipo_atividade,
            hh=item_chk.hh,
        )
        insumo = _item_material(item_chk.ins, ItemMaterial.Tipo.INSUMO, item_chk.un_i)
        if insumo and item_chk.qtd_i:
            AtividadeMaterial.objects.create(
                organizacao=org,
                atividade=atividade,
                item=insumo,
                qtd=item_chk.qtd_i,
                unidade=item_chk.un_i or "un",
            )
        peca = _item_material(item_chk.peca, ItemMaterial.Tipo.PECA, "un")
        if peca and item_chk.qtd_p:
            AtividadeMaterial.objects.create(
                organizacao=org, atividade=atividade, item=peca, qtd=item_chk.qtd_p, unidade="un"
            )

    return org
