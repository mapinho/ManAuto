"""`manage.py recalcula_plano [--org <slug>]`

Roda o recalculo do plano de forma sincrona (uso via CLI/ops — mesmo padrao
de `manage.py importar`). Uma view HTMX deve, em vez disso, enfileirar via
`apps/plano/tasks.py` (`.defer()`), nunca chamar `recalcular_plano` direto
no request. Sem `--org`, recalcula para todas as organizacoes cadastradas
(uso do `make plano`).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Organizacao

from ...services import recalcular_plano


class Command(BaseCommand):
    help = "Recalcula o plano anual de preventivas (motor) para uma ou todas as organizações."

    def add_arguments(self, parser):
        parser.add_argument("--org", help="slug da organização (padrão: todas)")

    def handle(self, *args, **options):
        if options["org"]:
            try:
                organizacoes = [Organizacao.objects.get(slug=options["org"])]
            except Organizacao.DoesNotExist as exc:
                raise CommandError(f"organização '{options['org']}' não encontrada") from exc
        else:
            organizacoes = list(Organizacao.objects.all())

        for organizacao in organizacoes:
            plano = recalcular_plano(organizacao)
            total_eventos = plano.eventos.count()
            self.stdout.write(
                f"{organizacao.slug}: plano #{plano.pk} — {total_eventos} evento(s) programado(s)."
            )
