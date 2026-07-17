"""Tipos de dominio do motor de calculo AgroVector.

Dataclasses puras (sem Django/ORM) que espelham as entidades do prototipo
JS v4.2 — ver SPEC_Funcional.md SS1-4 e SPEC_Tecnica_Ambiente.md SS3 para o
modelo de dados persistido (estes tipos sao a representacao de entrada/saida
do motor, nao o schema do banco).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class IndicesOficina:
    prev: float
    corr: float
    deflator: float
    terceiros: float = 0.0


@dataclass(frozen=True)
class DispOficina:
    h_brutas: float
    almoco: float
    cafe: float
    prod: float
    abs_: float
    ferias: float
    trein: float
    abr_os: float


@dataclass(frozen=True)
class Gatilho:
    valor: float
    tipo: str


@dataclass(frozen=True)
class GatilhosClasse:
    tipo_medida: str  # "Horas" | "KM"
    itvs: tuple[Gatilho, ...]


@dataclass(frozen=True)
class Premissas:
    oficinas: tuple[str, ...]
    indices: dict[str, IndicesOficina]
    disp: dict[str, DispOficina]
    dias_uteis: tuple[float, ...]  # 12 meses
    safra: tuple[bool, ...]  # 12 meses
    sazonal: tuple[float, ...]  # 12 meses
    gatilhos: dict[str, GatilhosClasse]
    inicio_safra: date
    fim_safra: date
    heranca: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Ativo:
    id: int
    nome: str
    classe: str
    status: str
    t_gat: str  # "Horas" | "KM"
    uso: float
    uso_med_safra: float
    uso_med_ent: float
    itv: float


@dataclass(frozen=True)
class Pessoa:
    id: int
    nome: str
    cargo: str
    oficina: str
    turno: str
    salario: float
    encargos: float
    status: str


@dataclass(frozen=True)
class ItemChecklist:
    id: int
    tipo_prev: str
    classe: str
    oficina: str
    atv: str
    cargo: str
    tipo_atividade: str
    hh: float
    ins: str = ""
    qtd_i: float = 0.0
    un_i: str = ""
    peca: str = ""
    qtd_p: float = 0.0


@dataclass(frozen=True)
class HorasLiquidas:
    efetivas: float
    liquidas: float


@dataclass(frozen=True)
class CustoPessoa:
    custo_mensal: float
    custo_hora: float


@dataclass(frozen=True)
class Semana:
    idx: int
    label: str
    data: date
    fim: date
    safra: bool
    mes: int  # 0-11, mes real (calendario) do inicio da semana


@dataclass(frozen=True)
class Cruzamento:
    """Um unico cruzamento de gatilho (n-esimo multiplo do intervalo) dentro de uma semana."""

    tipo: str
    hh: float
    cu: float


@dataclass(frozen=True)
class EntradaSemanal:
    tipo: str
    hh: float
    count: int
    prevs: tuple[Cruzamento, ...]
    safra: bool
    label: str
    mes: int


@dataclass(frozen=True)
class EntradaMensal:
    tipo: str
    hh: float
    count: int
    prevs: tuple[Cruzamento, ...]


@dataclass(frozen=True)
class EventoAgenda:
    data: date
    ativo: str
    classe: str
    tipo: str
    hh: float
    count: int
    oficina: str
    mecanico: str
    semana_idx: int
    safra: bool
