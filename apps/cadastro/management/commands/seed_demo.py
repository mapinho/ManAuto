from django.core.management.base import BaseCommand

from apps.cadastro.models import Ativo, Oficina, Pessoa
from apps.cadastro.seeding import semear_organizacao
from apps.motor.fixtures.dados_demo import checklist_demo, frota_demo, pessoas_demo, premissas_demo


class Command(BaseCommand):
    help = "Popula o banco com o dataset demo do prototipo (13 ativos, organizacao 'demo')."

    def handle(self, *args, **options):
        org = semear_organizacao(
            slug="demo",
            nome="Demo (protótipo v4.2)",
            premissas=premissas_demo(),
            frota=frota_demo(),
            pessoas=pessoas_demo(),
            checklist=checklist_demo(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Organização '{org.slug}' semeada: "
                f"{Oficina.objects.for_org(org).count()} oficinas, "
                f"{Ativo.objects.for_org(org).count()} ativos, "
                f"{Pessoa.objects.for_org(org).count()} pessoas."
            )
        )
