# Desenvolvimento AgroVector Manutenção — kit para Claude Code

Pasta com tudo que o time precisa para iniciar o desenvolvimento do produto no Claude Code.

## Conteúdo
- `SPEC_Funcional.md` — módulos, regras de negócio, motor de cálculo normativo (§3) e fixtures de regressão Petribú.
- `SPEC_Tecnica_Ambiente.md` — stack decidida (Django + PostgreSQL + Procrastinate + HTMX), arquitetura, modelo de dados, Docker Compose, CI e plano de migração do protótipo.
- `CLAUDE.md` — memória do repositório (regras que o Claude Code segue automaticamente).
- `.claude/skills/` — skills do projeto:
  - `agrovector-motor` — fórmulas normativas + fixtures (usar em qualquer cálculo)
  - `agrovector-dados` — modelo de dados, importadores e calibração por OS
  - `vector-relatorios` — identidade Vector, cores Fabio, regras de Excel/PPT/gráficos

## Como iniciar o repositório
1. Criar repo git `agrovector-manutencao` e copiar para a raiz: `CLAUDE.md`, `SPEC_Funcional.md`, `SPEC_Tecnica_Ambiente.md` e a pasta `.claude/`.
2. Copiar para `referencias/`: `agrovector_manutencao_v4.2_2026-06-16.html`, `agrovector_manutencao_Petribu_v1.0_2026-07-06.html` e `Planejamento_Manutencao_Petribu_v1.3.xlsx` (fonte dos fixtures).
3. Abrir o Claude Code na raiz e pedir: "Leia CLAUDE.md e as SPECs e execute o passo 1 do plano de migração (SPEC Técnica §6): scaffold do repo com Docker Compose e CI."
4. Seguir a ordem do §6: motor portado + fixtures Petribú passando ANTES de qualquer tela.

## Decisão de stack (resumo executivo)
PostgreSQL confirmado (banco e fila via Procrastinate — sem Redis por ora). Django 6 + DRF no backend; front do produto em Django/HTMX (não Streamlit — este fica para análises internas). Justificativas e alternativas na SPEC Técnica §1.
