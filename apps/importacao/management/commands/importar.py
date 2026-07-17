"""`manage.py importar --tipo <tipo> --org <slug> --arquivo <caminho>`

Roda o importador de forma síncrona (uso via CLI/ops) — uma view de upload
web deve, em vez disso, enfileirar via `apps/importacao/tasks.py`
(`.defer()`), nunca chamar o importador direto no request.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Organizacao
from apps.importacao.importadores.checklist import (
    importar_catalogo_itens,
    importar_checklist,
    importar_materiais_checklist,
)
from apps.importacao.importadores.frota import importar_frota
from apps.importacao.importadores.historico_os import importar_historico_os
from apps.importacao.importadores.pessoas import importar_pessoas

_IMPORTADORES = {
    "frota": importar_frota,
    "pessoas": importar_pessoas,
    "catalogo_itens": importar_catalogo_itens,
    "checklist": importar_checklist,
    "materiais_checklist": importar_materiais_checklist,
    "historico_os": importar_historico_os,
}


class Command(BaseCommand):
    help = "Importa uma planilha (templates Vector) para a organização informada."

    def add_arguments(self, parser):
        parser.add_argument("--tipo", required=True, choices=sorted(_IMPORTADORES))
        parser.add_argument("--org", required=True, help="slug da organização")
        parser.add_argument("--arquivo", required=True, help="caminho do CSV/XLSX")

    def handle(self, *args, **options):
        try:
            organizacao = Organizacao.objects.get(slug=options["org"])
        except Organizacao.DoesNotExist as exc:
            raise CommandError(f"organização '{options['org']}' não encontrada") from exc

        importador = _IMPORTADORES[options["tipo"]]
        resultado = importador(organizacao, options["arquivo"], origem_arquivo=options["arquivo"])

        self.stdout.write(
            f"{resultado.importados}/{resultado.total_linhas} linhas importadas "
            f"({len(resultado.erros)} erro(s))."
        )
        for erro in resultado.erros:
            self.stdout.write(self.style.WARNING(f"  linha {erro.linha}: {erro.mensagem}"))
