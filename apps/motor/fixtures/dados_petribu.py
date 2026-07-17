"""Dataset Petribu (384 ativos) — carregado de `dados_petribu.json`.

O JSON foi gerado executando o estado inicial `S` de
`referencias/agrovector_manutencao_Petribu_v1.0_2026-07-06.html` em Node.js
(nao foi transcrito a mao — ver skill agrovector-motor). Este arquivo so
converte o JSON em dataclasses do motor; a fonte da verdade dos dados e o
JSON, e a fonte da verdade do JSON e o prototipo HTML.

Observacao: esta instancia do Petribu nao tem pessoas cadastradas
(`S.pessoas` vazio) — os fixtures de regressao cobrem apenas
cronograma/plano preventivo/corretivo, nao disponibilidade/custo/saving.

Fonte unica de dados compartilhada por
`apps/motor/tests/test_fixture_petribu.py` e por `manage.py seed_petribu`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from apps.motor.tipos import (
    Ativo,
    DispOficina,
    Gatilho,
    GatilhosClasse,
    IndicesOficina,
    ItemChecklist,
    Pessoa,
    Premissas,
)

_JSON_PATH = Path(__file__).resolve().parent / "dados_petribu.json"


def _carregar_json() -> dict:
    with _JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _parse_data_iso(s: str) -> date:
    ano, mes, dia = (int(p) for p in s.split("-"))
    return date(ano, mes, dia)


def premissas_petribu() -> Premissas:
    dados = _carregar_json()
    prem = dados["premissas"]
    return Premissas(
        oficinas=tuple(dados["oficinas"]),
        indices={
            of: IndicesOficina(
                prev=v["prev"],
                corr=v["corr"],
                deflator=v["deflator"],
                terceiros=v.get("terceiros", 0),
            )
            for of, v in prem["indices"].items()
        },
        disp={
            of: DispOficina(
                h_brutas=v["hBrutas"],
                almoco=v["almoco"],
                cafe=v["cafe"],
                prod=v["prod"],
                abs_=v["abs"],
                ferias=v["ferias"],
                trein=v["trein"],
                abr_os=v["abrOS"],
            )
            for of, v in prem["disp"].items()
        },
        dias_uteis=tuple(prem["diasUteis"]),
        safra=tuple(prem["safra"]),
        sazonal=tuple(prem["sazonal"]),
        gatilhos={
            classe: GatilhosClasse(
                tipo_medida=g["tipo"],
                itvs=tuple(Gatilho(valor=iv["v"], tipo=iv["t"]) for iv in g["itvs"]),
            )
            for classe, g in prem["gatilhos"].items()
        },
        inicio_safra=_parse_data_iso(prem["inicioSafra"]),
        fim_safra=_parse_data_iso(prem["fimSafra"]),
        heranca={tipo: tuple(v) for tipo, v in prem["heranca"].items()},
    )


def frota_petribu() -> list[Ativo]:
    dados = _carregar_json()
    return [
        Ativo(
            id=a["id"],
            nome=a["nome"],
            classe=a["classe"],
            status=a["status"],
            t_gat=a["tGat"],
            uso=a["uso"],
            uso_med_safra=a["usoMedSafra"],
            uso_med_ent=a["usoMedEnt"],
            itv=a["itv"],
        )
        for a in dados["frota"]
    ]


def pessoas_petribu() -> list[Pessoa]:
    dados = _carregar_json()
    return [
        Pessoa(
            id=p["id"],
            nome=p["nome"],
            cargo=p["cargo"],
            oficina=p["oficina"],
            turno=p["turno"],
            salario=p["sal"],
            encargos=p["enc"],
            status=p["status"],
        )
        for p in dados["pessoas"]
    ]


def checklist_petribu() -> list[ItemChecklist]:
    dados = _carregar_json()
    return [
        ItemChecklist(
            id=c["id"],
            tipo_prev=c["tipoPrev"],
            classe=c["classe"],
            oficina=c["oficina"],
            atv=c["atv"],
            cargo=c["cargo"],
            tipo_atividade=c["tipo"],
            hh=c["hh"],
            ins=c.get("ins", ""),
            qtd_i=c.get("qtdI", 0.0),
            un_i=c.get("unI", ""),
            peca=c.get("peca", ""),
            qtd_p=c.get("qtdP", 0.0),
        )
        for c in dados["checklist"]
    ]
