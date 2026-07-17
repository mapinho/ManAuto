"""Historico de Ordens de Servico importado — base da calibracao por OS.

Os parsers/tasks de importacao (apps/importacao/parsers.py,
apps/importacao/tasks.py) sao o passo 4 do plano de migracao
(SPEC_Tecnica_Ambiente.md SS6) — aqui so o model de persistencia.
"""

from django.db import models

from apps.cadastro.models import Ativo, Oficina
from apps.core.models import ImportadoMixin, OrgScopedModel


class OrdemServico(OrgScopedModel, ImportadoMixin):
    """`id_externo` guarda o `id_os` do importador (template_historico_os)."""

    ativo = models.ForeignKey(
        Ativo, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_servico"
    )
    data = models.DateField(help_text="data_abertura no importador")
    data_fechamento = models.DateField(null=True, blank=True)
    tipo_os = models.CharField(max_length=100)
    oficina = models.ForeignKey(
        Oficina, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_servico"
    )
    sistema_falha = models.CharField(max_length=200, blank=True)
    descricao_falha = models.TextField(blank=True)
    mecanico_responsavel = models.CharField(max_length=200, blank=True)
    custo_hh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    custo_pecas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hh_executadas = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    horimetro = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="medicao_na_os"
    )

    class Meta:
        verbose_name = "Ordem de serviço"
        verbose_name_plural = "Ordens de serviço"
        ordering = ["-data"]
        unique_together = ("organizacao", "id_externo")

    def __str__(self) -> str:
        return f"OS {self.id_externo or self.pk} — {self.ativo} @ {self.data}"
