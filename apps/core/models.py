"""Organizacoes, estrutura (filial/setor) e papeis (RBAC).

`OrgScopedModel` e o manager `for_org()` sao a base do isolamento multi-tenant
(CLAUDE.md): todo model de negocio herda daqui, e toda query de request deve
passar por `.objects.for_org(organizacao)` em vez de `.objects.all()`.
"""

from django.conf import settings
from django.db import models


class Organizacao(models.Model):
    nome = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"

    def __str__(self) -> str:
        return self.nome


class OrgQuerySet(models.QuerySet):
    def for_org(self, organizacao: Organizacao) -> OrgQuerySet:
        return self.filter(organizacao=organizacao)


class OrgScopedModel(models.Model):
    """Abstrato: toda entidade de negocio pertence a uma Organizacao.

    Usar sempre `Model.objects.for_org(organizacao)` em codigo de request —
    nunca `Model.objects.all()` (CLAUDE.md, regras de arquitetura).
    """

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE, related_name="+")

    objects = OrgQuerySet.as_manager()

    class Meta:
        abstract = True


class ImportadoMixin(models.Model):
    """Rastreabilidade de dados carregados via importador (SPEC_Tecnica_Ambiente.md SS4).

    `id_externo` e a chave natural do registro na planilha/sistema do
    cliente (ex.: id_ativo, id_funcionario, id_os) — usada para upsert em
    reimportacoes. `null=True` (em vez de so `blank=True`) para que multiplos
    registros sem id_externo (ex.: dados semeados por `seed_demo`) nao
    colidam na constraint de unicidade por organizacao.
    """

    id_externo = models.CharField(  # noqa: DJ001 - null=True e intencional, ver docstring
        max_length=100, null=True, blank=True, default=None
    )
    origem_arquivo = models.CharField(max_length=300, blank=True)
    carregado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class Filial(OrgScopedModel):
    nome = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = "Filiais"
        unique_together = ("organizacao", "nome")

    def __str__(self) -> str:
        return self.nome


class Setor(OrgScopedModel):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="setores")
    nome = models.CharField(max_length=200)

    class Meta:
        unique_together = ("filial", "nome")

    def __str__(self) -> str:
        return f"{self.filial} / {self.nome}"


class Papel(models.TextChoices):
    """SPEC_Funcional.md SS4: papeis multi-tenant."""

    ADMIN_VECTOR = "admin_vector", "Admin Vector"
    CONSULTOR = "consultor", "Consultor"
    GESTOR_CLIENTE = "gestor_cliente", "Gestor Cliente"
    PCM = "pcm", "PCM"
    LEITURA = "leitura", "Leitura"


class Membro(OrgScopedModel):
    """Vinculo usuario <-> organizacao com papel.

    Gestao de usuarios e restrita a admins Vector e consultores
    (SPEC_Funcional.md SS1) — a UI/permissao que aplica essa regra vem numa
    fase de autenticacao futura; este model so guarda o vinculo.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membros"
    )
    papel = models.CharField(max_length=20, choices=Papel.choices)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organizacao", "usuario")

    def __str__(self) -> str:
        return f"{self.usuario} @ {self.organizacao} ({self.papel})"
