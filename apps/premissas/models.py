"""Premissas versionadas (calendario agricola) — SPEC_Tecnica_Ambiente.md SS3.

Indices por oficina (%prev, %corr, deflator, %terceiros) e disponibilidade de
MO vivem no model `Oficina` (apps/cadastro) — nao sao versionados aqui.
`ConjuntoPremissas` versiona apenas o calendario: dias uteis/mes, sazonal,
datas de safra e a tabela de heranca.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import OrgScopedModel


class ConjuntoPremissas(OrgScopedModel):
    """`calendario` (JSONB): dias_uteis[12], sazonal[12], inicio_safra,
    fim_safra, heranca — ver apps/motor/tipos.py:Premissas para o shape
    esperado pelo motor.
    """

    versao = models.PositiveIntegerField()
    vigente = models.BooleanField(default=False)
    calendario = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ("organizacao", "versao")
        ordering = ["-versao"]

    def __str__(self) -> str:
        return f"{self.organizacao} — v{self.versao}" + (" (vigente)" if self.vigente else "")
