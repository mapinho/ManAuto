# SPEC Técnica e Ambiente — AgroVector Manutenção

Versão 1.0 · 07/07/2026

## 1. Avaliação da stack proposta (Fabio) e recomendação

| Proposta inicial | Avaliação | Recomendação |
|---|---|---|
| PostgreSQL (banco) | ✅ Correta. Relacional, JSONB para premissas versionadas, window functions para os planos. | **PostgreSQL 16** — decisão fechada. |
| PostgreSQL (mensageria) | ✅ Viável e recomendado NESTA escala. Evita Redis/RabbitMQ como infraestrutura extra. | **Procrastinate** (fila de tarefas Python nativa em Postgres, usa LISTEN/NOTIFY). Se o volume crescer muito (>50 jobs/s), migrar para Celery+Redis — a interface de tasks fica isolada para permitir troca. |
| Python/Django | ✅ Correta. Admin pronto (CRUDs de cadastro), ORM, auth/permissões, ecossistema maduro — ideal para time enxuto guiado por Claude Code. | **Django 6 + Django REST Framework** (API para futuros clientes mobile/integrações). |
| Streamlit | ⚠️ Ótimo para protótipos e análises internas; NÃO recomendado como front do produto multiusuário (auth/permissões limitadas, estado por sessão, difícil UX de agenda/grades 384×52). | Front do produto: **Django templates + HTMX + Alpine.js** (server-driven, simples de manter) com **ECharts** para gráficos. Streamlit fica como **ferramenta interna de análise/calibração** (ler OS, gerar sazonalidade) — opcional. |

Resumo da decisão: **monolito Django + PostgreSQL + Procrastinate**, front HTMX, API DRF. Zero microsserviço — simplicidade operacional primeiro, o gargalo do negócio é validação de premissas, não escala.

### ADR-0001 — Bump Python 3.12→3.14 e Django 5→6

**Status:** aceito, 16/07/2026.
**Contexto:** a decisão original (v1.0) fixou Python 3.12 + Django 5. Antes do scaffold do repositório (§6 passo 1), Django 6 e Python 3.14 já eram as versões estáveis correntes, e o ambiente local de desenvolvimento já usa Python 3.14.
**Decisão:** adotar Python 3.14 + Django 6 como stack corrente. Sem mudança de arquitetura (§2) ou modelo de dados (§3) — apenas bump de versão.
**Consequências:** `pyproject.toml`, `Dockerfile`, `.python-version` e o workflow de CI passam a fixar 3.14/Django 6. Revisitar dependências de terceiros (`procrastinate`, `django-simple-history`, `django-htmx`) quanto à compatibilidade com Django 6 no passo 2.

## 2. Arquitetura

```
┌────────────────────────────────────────────────────────┐
│ Django (monolito)                                      │
│  apps/                                                 │
│   core/       organizações, usuários, papéis (RBAC)   │
│   cadastro/   oficinas, classes, ativos, pessoas,      │
│               checklists, gatilhos, materiais          │
│   premissas/  premissas versionadas + cenários (JSONB) │
│   motor/      cálculo puro (sem Django!) — portado do  │
│               JS do protótipo, 100% testável           │
│   plano/      cronograma, agenda, planos, saving       │
│               (persistência dos resultados do motor)   │
│   importacao/ CSV/XLSX + calibração por histórico OS   │
│   relatorios/ export Excel (openpyxl) e PPT (python-pptx)│
│  API: DRF /api/v1 · UI: templates + HTMX               │
├────────────────────────────────────────────────────────┤
│ Procrastinate (jobs em Postgres): recálculo de plano,  │
│ imports pesados, geração de relatórios                 │
├────────────────────────────────────────────────────────┤
│ PostgreSQL 16 (dados + fila + LISTEN/NOTIFY)           │
└────────────────────────────────────────────────────────┘
```

**Regra de ouro:** `apps/motor/` é Python puro (dataclasses, sem ORM) — porta fiel das funções do protótipo (`calcHL`, `detTipo`, `getHeranca`, `calcCronogramaSemanal`, `calcPlanPrev`, `calcPlanCorr`, `calcDispMes`, `custoHHOf`, `buildAgendaEventos`). Entradas/saídas tipadas. É o coração do produto e tem suíte de regressão própria (fixtures Petribú).

## 3. Modelo de dados (núcleo)

```
Organizacao ─< Filial ─< Setor
Organizacao ─< Oficina (nome, índices: prev%, corr%, deflator, terceiros%, disp_mo JSONB)
Organizacao ─< ClasseAtivo (nome, unidade h/km) ─< Gatilho (tipo S..D, intervalo, ordem)
Organizacao ─< Ativo (classe FK, setor FK, status, tipo_gatilho, uso_atual,
                       uso_sem_safra, uso_sem_entressafra, intervalo, garantia)
Ativo ─< MedicaoUso (data, valor)                 ← histórico de horímetro
Organizacao ─< Pessoa (oficina FK, cargo, turno, salario, encargos, status)
ClasseAtivo ─< ChecklistAtividade (tipo_prev, oficina FK, descricao, cargo,
                                   tipo_atividade, hh)
ChecklistAtividade ─< AtividadeMaterial (item FK, qtd, unidade)
Organizacao ─< ItemMaterial (descricao, tipo, unidade, custo_unitario)
Organizacao ─< ConjuntoPremissas (versão, vigente bool, calendario JSONB:
               dias_uteis[12], sazonal[12], inicio/fim_safra, heranca)
ConjuntoPremissas ─< PlanoAnual (status rascunho/aprovado; resultados persistidos:
               EventoPreventiva[data, ativo, tipo, hh, oficina, responsavel, status_execucao])
Organizacao ─< OrdemServico (historico importado: data, ativo, tipo_os, oficina,
               sistema_falha, custo_total, hh_executadas, horimetro)
```

Auditoria: `django-simple-history` nas premissas e cadastros.

## 4. Ambiente de desenvolvimento

- **Python 3.14 + uv** (gestão de deps e venv) · lint/format **ruff** · testes **pytest + pytest-django** · **pre-commit**.
- **Docker Compose**: serviços `web` (Django), `worker` (Procrastinate), `db` (postgres:16). Um comando: `docker compose up`.
- **Makefile**: `make dev / test / lint / seed-petribu / plano`.
- Seeds: `manage.py seed_demo` (dados do protótipo) e `manage.py seed_petribu` (384 ativos + premissas calibradas) — base dos testes de regressão.
- CI: **GitHub Actions** (lint + pytest + cobertura mínima 85% no app `motor/`).
- Branches: trunk-based (main protegida + PRs curtos). Claude Code trabalha por PR.

```yaml
# docker-compose.yml (esqueleto)
services:
  db:
    image: postgres:16
    environment: {POSTGRES_DB: agrovector, POSTGRES_PASSWORD: dev}
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5432:5432"]
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes: [.:/app]
    ports: ["8000:8000"]
    depends_on: [db]
  worker:
    build: .
    command: python manage.py procrastinate worker
    depends_on: [db]
volumes: {pgdata: {}}
```

Dependências iniciais: `django djangorestframework procrastinate[django] psycopg[binary] openpyxl python-pptx pandas django-simple-history django-htmx whitenoise gunicorn pytest pytest-django ruff`.

## 5. Produção

- **Fase piloto (Petribú + 2–3 clientes)**: 1 VPS (Hetzner/Contabo 8GB) com Docker Compose + Caddy (TLS automático) OU PaaS (Railway/Render) para zero-ops. Backup: `pg_dump` diário → S3/Backblaze + teste de restore mensal.
- **Escala**: separar Postgres gerenciado (Supabase/RDS/Neon), 2+ réplicas web atrás de load balancer, workers dedicados.
- Observabilidade: Sentry (erros) + logs estruturados; healthcheck `/healthz`.
- Segurança: RBAC por organização em TODAS as queries (manager `for_org()` obrigatório), HTTPS, senhas Argon2, LGPD (dados de salário → coluna criptografada `pgcrypto` e permissão restrita).

## 6. Migração do protótipo (ordem de trabalho no Claude Code)

1. Scaffold do repo (estrutura acima) + Compose + CI.
2. Portar o motor JS → `apps/motor/` (Python puro) e fazer os fixtures Petribú passarem (paridade < 0,1%).
3. Modelos + admin + seeds.
4. Importadores (templates Vector) + calibração por OS.
5. Telas HTMX na ordem do roadmap R1 (Premissas → Frota → Pessoas → Checklist → Cronograma → Agenda → Disponibilidade).
6. Export Excel (paridade com planilha v1.3), depois PPT.

## 7. Estimativa de esforço (com Claude Code)
R1 (MVP): 4–6 semanas de 1 dev orientando Claude Code · R2: +3–4 semanas · R3: +3–4 semanas. Premissa: fixtures de regressão desde a semana 1 — o motor validado é o que protege o produto.
