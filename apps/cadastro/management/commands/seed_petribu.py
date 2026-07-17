from django.core.management.base import BaseCommand

from apps.cadastro.models import Ativo, Oficina, Pessoa
from apps.cadastro.seeding import semear_organizacao
from apps.motor.fixtures.dados_petribu import (
    checklist_petribu,
    frota_petribu,
    pessoas_petribu,
    premissas_petribu,
)


class Command(BaseCommand):
    help = "Popula o banco com o dataset Petribú (384 ativos, organizacao 'petribu')."

    def handle(self, *args, **options):
        org = semear_organizacao(
            slug="petribu",
            nome="Petribú",
            premissas=premissas_petribu(),
            frota=frota_petribu(),
            pessoas=pessoas_petribu(),
            checklist=checklist_petribu(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Organização '{org.slug}' semeada: "
                f"{Oficina.objects.for_org(org).count()} oficinas, "
                f"{Ativo.objects.for_org(org).count()} ativos, "
                f"{Pessoa.objects.for_org(org).count()} pessoas."
            )
        )
