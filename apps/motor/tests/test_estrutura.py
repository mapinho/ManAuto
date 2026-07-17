"""Teste estrutural: garante que apps/motor permanece Python puro (CLAUDE.md).

As formulas normativas (SPEC_Funcional.md SS3) e os fixtures de
regressao Petribu entram no passo 2 do plano de migracao
(SPEC_Tecnica_Ambiente.md SS6); este teste protege a regra de
arquitetura desde o scaffold.
"""

import ast
from pathlib import Path

MOTOR_DIR = Path(__file__).resolve().parent.parent

PROIBIDOS = ("django",)


def _modulos_python():
    return [p for p in MOTOR_DIR.rglob("*.py") if "tests" not in p.relative_to(MOTOR_DIR).parts]


def test_motor_nao_importa_django():
    for modulo in _modulos_python():
        arvore = ast.parse(modulo.read_text(encoding="utf-8"), filename=str(modulo))
        for node in ast.walk(arvore):
            if isinstance(node, ast.Import):
                nomes = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                nomes = [node.module or ""]
            else:
                continue
            for nome in nomes:
                assert not nome.startswith(PROIBIDOS), (
                    f"{modulo} importa '{nome}': apps/motor deve ser Python puro"
                )
