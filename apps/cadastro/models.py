"""Cadastro: oficinas, classes, ativos, pessoas, checklists, gatilhos, materiais.

SPEC_Tecnica_Ambiente.md SS3. Oficinas e classes sao configuraveis por
organizacao — nunca hardcodar nomes (CLAUDE.md).
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import ImportadoMixin, OrgScopedModel, Setor


class TipoPreventiva(models.TextChoices):
    """Herança cumulativa S⊂A⊂B⊂C⊂D — SPEC_Funcional.md SS3.3."""

    S = "S", "Simples"
    A = "A", "Intermediária"
    B = "B", "Completa"
    C = "C", "Grande porte"
    D = "D", "Reforma"


class Unidade(models.TextChoices):
    """Valores batem com o motor (apps/motor/tipos.py: t_gat/tipo_medida) — 'Horas'/'KM'."""

    HORAS = "Horas", "Horas"
    KM = "KM", "Quilômetros"


class Oficina(OrgScopedModel):
    """Indices (%prev, %corr, deflator, %terceiros) e disponibilidade de MO.

    `disp_mo` guarda os 8 parametros de horas liquidas (SPEC_Funcional.md
    SS3.1): h_brutas, almoco, cafe, prod, abs, ferias, trein, abr_os.
    """

    nome = models.CharField(max_length=200)
    prev_pct = models.DecimalField("% preventiva", max_digits=5, decimal_places=2)
    corr_pct = models.DecimalField("% corretiva", max_digits=5, decimal_places=2)
    deflator_pct = models.DecimalField("deflator % a.a.", max_digits=5, decimal_places=2)
    terceiros_pct = models.DecimalField("% terceiros", max_digits=5, decimal_places=2, default=0)
    disp_mo = models.JSONField("disponibilidade de MO", default=dict)

    history = HistoricalRecords()

    class Meta:
        unique_together = ("organizacao", "nome")

    def __str__(self) -> str:
        return self.nome


class ClasseAtivo(OrgScopedModel):
    nome = models.CharField(max_length=200)
    unidade = models.CharField(max_length=10, choices=Unidade.choices)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Classe de ativo"
        verbose_name_plural = "Classes de ativo"
        unique_together = ("organizacao", "nome")

    def __str__(self) -> str:
        return self.nome


class Gatilho(OrgScopedModel):
    """Intervalo de disparo de preventiva por tipo (S/A/B/C/D) — SPEC_Funcional.md SS3.2."""

    classe = models.ForeignKey(ClasseAtivo, on_delete=models.CASCADE, related_name="gatilhos")
    tipo = models.CharField(max_length=1, choices=TipoPreventiva.choices)
    intervalo = models.DecimalField(max_digits=10, decimal_places=2)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("classe", "tipo")
        ordering = ["ordem"]

    def __str__(self) -> str:
        return f"{self.classe} — {self.tipo} ({self.intervalo})"


class Ativo(OrgScopedModel, ImportadoMixin):
    class Status(models.TextChoices):
        ATIVO = "Ativo", "Ativo"
        REFORMA = "Reforma", "Reforma"
        INATIVO = "Inativo", "Inativo"
        VENDIDO = "Vendido", "Vendido"

    nome = models.CharField(max_length=200)
    classe = models.ForeignKey(ClasseAtivo, on_delete=models.PROTECT, related_name="ativos")
    setor = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="ativos"
    )
    oficina = models.ForeignKey(
        Oficina,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ativos",
        help_text=(
            "Oficina responsável (informativo — o motor apura a oficina por evento via checklist)."
        ),
    )
    modelo = models.CharField(max_length=200, blank=True)
    fabricante = models.CharField(max_length=200, blank=True)
    subclasse = models.CharField(max_length=200, blank=True)
    placa_serie = models.CharField(max_length=50, blank=True)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVO)
    tipo_gatilho = models.CharField(max_length=10, choices=Unidade.choices)
    uso_atual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    uso_sem_safra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    uso_sem_entressafra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    intervalo = models.DecimalField(max_digits=10, decimal_places=2)
    garantia = models.BooleanField(default=False)
    tipo_preventiva_atual = models.CharField(
        max_length=1, choices=TipoPreventiva.choices, blank=True
    )
    ultima_prev_data = models.DateField(null=True, blank=True)
    ultima_prev_medicao = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ("organizacao", "id_externo")

    def __str__(self) -> str:
        return self.nome


class MedicaoUso(OrgScopedModel):
    """Historico de horimetro/hodometro de um ativo."""

    ativo = models.ForeignKey(Ativo, on_delete=models.CASCADE, related_name="medicoes")
    data = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-data"]

    def __str__(self) -> str:
        return f"{self.ativo} @ {self.data}: {self.valor}"


class Pessoa(OrgScopedModel, ImportadoMixin):
    """Salario/encargos: acesso deve ser restrito (permissao propria + pgcrypto).

    Criptografia em coluna e a permissao dedicada ainda NAO estao
    implementadas — SPEC_Tecnica_Ambiente.md SS5 exige isso para producao;
    ficou fora do escopo deste passo (modelos + admin + seeds).
    """

    class Status(models.TextChoices):
        ATIVO = "Ativo", "Ativo"
        INATIVO = "Inativo", "Inativo"
        FERIAS = "Férias", "Férias"
        AFASTADO = "Afastado", "Afastado"

    class Turno(models.TextChoices):
        DIURNO = "Diurno", "Diurno"
        NOTURNO = "Noturno", "Noturno"
        SAFRA = "Safra", "Safra"
        TURNO_5X1 = "Turno 5x1", "Turno 5x1"

    nome = models.CharField(max_length=200)
    oficina = models.ForeignKey(Oficina, on_delete=models.PROTECT, related_name="pessoas")
    setor = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="pessoas"
    )
    cargo = models.CharField(max_length=200)
    tipo_mo = models.CharField(
        max_length=100,
        blank=True,
        help_text="Classificação de mão de obra do importador (tipo_mo).",
    )
    turno = models.CharField(max_length=20, choices=Turno.choices)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    encargos_pct = models.DecimalField(max_digits=5, decimal_places=2)
    horas_contratuais_dia = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVO)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Pessoas"
        unique_together = ("organizacao", "id_externo")

    def __str__(self) -> str:
        return self.nome


class ChecklistAtividade(OrgScopedModel, ImportadoMixin):
    """Atividade de checklist por classe x tipo de preventiva.

    HH e incremental por tipo — a heranca (soma S⊂A⊂B⊂C⊂D) e aplicada pelo
    motor (apps/motor/heranca.py), nunca aqui. `id_externo` guarda o
    `id_atividade` do importador; `id_checklist`/`nome_checklist` agrupam as
    atividades de uma mesma revisão (ex.: "CKL-A-TRA" = "Preventiva A Trator").

    A chave natural e (`id_checklist`, `id_externo`), NAO so `id_externo`:
    o mesmo `id_atividade` (ex.: "troca de óleo") se repete em varios
    checklists, ja que a revisão B inclui os itens da A (herança
    cumulativa) — `template_pecas_insumos` vincula materiais tambem pela
    dupla (id_checklist, id_atividade), nunca so por id_atividade.
    """

    classe = models.ForeignKey(ClasseAtivo, on_delete=models.CASCADE, related_name="checklist")
    tipo_prev = models.CharField(max_length=1, choices=TipoPreventiva.choices)
    oficina = models.ForeignKey(
        Oficina, on_delete=models.PROTECT, related_name="atividades_checklist"
    )
    id_checklist = models.CharField(max_length=100, blank=True)
    nome_checklist = models.CharField(max_length=300, blank=True)
    seq = models.PositiveSmallIntegerField(default=0)
    descricao = models.CharField(max_length=300)
    cargo = models.CharField(max_length=200)
    tipo_atividade = models.CharField(max_length=50)
    hh = models.DecimalField(max_digits=6, decimal_places=2)
    observacao = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Atividade de checklist"
        verbose_name_plural = "Atividades de checklist"
        unique_together = ("organizacao", "id_checklist", "id_externo")
        ordering = ["id_checklist", "seq"]

    def __str__(self) -> str:
        return f"{self.classe} — {self.tipo_prev} — {self.descricao}"


class ItemMaterial(OrgScopedModel, ImportadoMixin):
    class Tipo(models.TextChoices):
        INSUMO = "insumo", "Insumo"
        PECA = "peca", "Peça"

    descricao = models.CharField(max_length=300)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    subtipo = models.CharField(max_length=100, blank=True)
    unidade = models.CharField(max_length=20)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fornecedor_principal = models.CharField(max_length=200, blank=True)
    codigo_fabricante = models.CharField(max_length=100, blank=True)
    observacao = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ("organizacao", "id_externo")

    def __str__(self) -> str:
        return self.descricao


class AtividadeMaterial(OrgScopedModel):
    atividade = models.ForeignKey(
        ChecklistAtividade, on_delete=models.CASCADE, related_name="materiais"
    )
    item = models.ForeignKey(ItemMaterial, on_delete=models.PROTECT, related_name="usos")
    qtd = models.DecimalField(max_digits=10, decimal_places=3)
    unidade = models.CharField(max_length=20)

    class Meta:
        verbose_name_plural = "Materiais de atividade"

    def __str__(self) -> str:
        return f"{self.atividade} — {self.item} x{self.qtd}"
