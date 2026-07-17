"""Plano anual e agenda de preventivas — persistencia dos resultados do motor.

Estes models NUNCA calculam nada (CLAUDE.md: motor e o unico lugar com
formulas) — sao apenas o resultado persistido de rodar apps/motor/ sobre um
ConjuntoPremissas + cadastro vigentes.
"""

from django.db import models

from apps.cadastro.models import Ativo, Oficina, Pessoa, TipoPreventiva
from apps.core.models import OrgScopedModel
from apps.premissas.models import ConjuntoPremissas


class PlanoAnual(OrgScopedModel):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        APROVADO = "aprovado", "Aprovado"

    conjunto_premissas = models.ForeignKey(
        ConjuntoPremissas, on_delete=models.PROTECT, related_name="planos"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Plano {self.conjunto_premissas} ({self.status})"


class EventoPreventiva(OrgScopedModel):
    class StatusExecucao(models.TextChoices):
        PROGRAMADA = "programada", "Programada"
        REALIZADA = "realizada", "Realizada"
        REPROGRAMADA = "reprogramada", "Reprogramada"
        CANCELADA = "cancelada", "Cancelada"

    plano_anual = models.ForeignKey(PlanoAnual, on_delete=models.CASCADE, related_name="eventos")
    data = models.DateField()
    ativo = models.ForeignKey(Ativo, on_delete=models.PROTECT, related_name="eventos_preventiva")
    tipo = models.CharField(max_length=1, choices=TipoPreventiva.choices)
    hh = models.DecimalField(max_digits=6, decimal_places=2)
    oficina = models.ForeignKey(
        Oficina, on_delete=models.PROTECT, related_name="eventos_preventiva"
    )
    responsavel = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_preventiva",
    )
    status_execucao = models.CharField(
        max_length=20, choices=StatusExecucao.choices, default=StatusExecucao.PROGRAMADA
    )

    class Meta:
        ordering = ["data"]

    def __str__(self) -> str:
        return f"{self.ativo} — {self.tipo} @ {self.data}"
