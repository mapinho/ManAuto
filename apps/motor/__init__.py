"""Motor de calculo AgroVector.

Python puro (dataclasses, sem Django/ORM) — ver CLAUDE.md e
.claude/skills/agrovector-motor/SKILL.md. Formulas normativas em
SPEC_Funcional.md SS3. Porta fiel das funcoes JS do prototipo
(calcHL, detTipo, getHeranca, calcCronogramaSemanal, calcPlanPrev,
calcPlanCorr, calcDispMes, custoHHOf, buildAgendaEventos).

Fixture de regressao do dataset demo (13 ativos) em
apps/motor/tests/test_fixture_demo.py. O fixture Petribu (384 ativos,
SPEC_Funcional.md SS3.6) depende da fonte
`agrovector_manutencao_Petribu_v1.0_2026-07-06.html` /
`Planejamento_Manutencao_Petribu_v1.3.xlsx` (README.md passo 2), ainda
nao presente no repositorio.
"""
