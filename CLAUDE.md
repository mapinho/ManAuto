# CLAUDE.md — Repositório AgroVector Manutenção

Contexto: produto SaaS de planejamento de manutenção para agronegócio da Vector Consulting. Este contexto e os documentos aqui citados foram gerados pelo Claude Desktop para o desenvolvimento da app `agrovector_manutencao_v4.2_2026-06-16.html` que foi criado pelo prompt `PROMPT_Planejamento_Manutencao_Excel.md`.
Documentos normativos: `SPEC_Funcional.md` (regras de negócio e motor) e `SPEC_Tecnica_Ambiente.md` (arquitetura e stack). Em conflito, as SPECs vencem.

## Stack (não mudar sem ADR)
Python 3.14 · Django 6 + DRF · PostgreSQL 16 · Procrastinate (fila em Postgres) · HTMX + Alpine + ECharts · uv · pytest · ruff · Docker Compose.

## Regras de arquitetura
- `apps/motor/` é **Python puro** (sem imports de Django/ORM). Toda regra de cálculo vive lá, com tipos explícitos. Views/serviços chamam o motor, nunca reimplementam fórmulas.
- Multi-tenant: TODA query passa por `Model.objects.for_org(org)`. Nunca usar `objects.all()` em código de request.
- Jobs longos (recálculo de plano, import, relatórios) SEMPRE via Procrastinate, nunca no request.
- Migrations pequenas e reversíveis; nunca editar migration aplicada.

## Regras do motor de cálculo (críticas)
As fórmulas do SPEC Funcional §3 são normativas (horas líquidas, detTipo, herança S⊂A⊂B⊂C⊂D, deflator progressivo `1−(defl/100)×(m/11+0.5)×0.5`, sazonalidade, saving). Qualquer alteração exige: aprovação do Fabio + atualização da SPEC + novo fixture.
Testes de regressão obrigatórios (dataset Petribú, `make seed-petribu`): 384 ativos → 2.101±1 preventivas/ano, 7.984 HH prev (±0,1%), 22.761 HH corr (±0,1%). PR que quebra esses números não passa.

## Padrões visuais (obrigatórios em UI e relatórios)
- Identidade Vector: azul #1F3060, cinza #B2B5B7.
- Cores Fabio (semáforo): verde #00FF00 · amarelo #FFFF00 · vermelho #FF3300. **Fundo vermelho → texto branco, sempre.** Verde/amarelo → texto preto.
- Todo gráfico com rótulos de dados visíveis; pizza/rosca obrigatoriamente em %.
- Cronograma/agenda: S verde, A amarelo, B/C vermelho.

## Convenções de código
- Idioma: código e identificadores em pt-BR sem acentos (`plano_preventiva`, `horas_liquidas`); docstrings pt-BR.
- Testes primeiro no motor; cobertura mínima 85% em `apps/motor/`.
- Commits convencionais (`feat:`, `fix:`, `test:`...), PRs pequenos com descrição do que validar.
- Rodar `make lint test` antes de todo commit.

## Skills disponíveis (.claude/skills/)
- `agrovector-motor` — regras e fixtures do motor de cálculo; usar ao implementar/alterar qualquer cálculo.
- `agrovector-dados` — modelo de dados, importadores e formatos dos templates Vector; usar em models/migrations/imports.
- `vector-relatorios` — padrões de exportação Excel/PPT e cores Fabio; usar em qualquer relatório ou gráfico.

## O que NÃO fazer
- Não introduzir Redis/Celery/microsserviços sem ADR aprovado.
- Não usar Streamlit no produto (apenas em `tools/` para análises internas).
- Não hardcodar oficinas/classes (são configuráveis por organização).
- Não colocar cálculo em template/JS — motor é backend.
