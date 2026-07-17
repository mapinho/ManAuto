---
name: agrovector-motor
description: Regras normativas e fixtures do motor de cálculo AgroVector (cronograma 52 semanas, herança S/A/B/C/D, planos preventivo/corretivo, disponibilidade, saving). Usar SEMPRE que implementar, alterar ou revisar qualquer cálculo em apps/motor/, ou quando testes de regressão Petribú falharem.
---

# Motor de cálculo AgroVector

Implementação em `apps/motor/` — Python puro, sem Django. Fonte original: funções JS do protótipo v4.2 (`calcHL`, `detTipo`, `getHeranca`, `calcHHChk`, `calcCronogramaSemanal`, `calcCronograma`, `calcPlanPrev`, `calcPlanCorr`, `calcDispMes`, `calcCusto`, `custoHHOf`, `buildAgendaEventos`).

## Fórmulas normativas

1. **Horas líquidas/dia** (por oficina):
   `efetivas = max(0, h_brutas − almoco − cafe − abertura_os)`
   `fA = abs/100 + ferias/100/12 + trein/(252×efetivas)  # trein em h/ano`
   `liquidas = efetivas × (1 − min(fA, 0.99)) × (prod/100)`
2. **Semanas**: 52 a partir de `inicio_safra`; semana é safra se `inicio ≤ data_inicio_semana ≤ fim_safra`. Mês do evento = mês da data de início da semana.
3. **Disparo de preventiva** (por ativo, por semana):
   `uso_semana = uso_sem_safra if safra else uso_sem_entressafra`
   dispara quando `floor((acum+uso)/itv) > floor(acum/itv)`; gerar UM evento por cruzamento `n` (pode haver >1 na semana).
4. **Tipo do evento** em `cu = n×itv`: iterar gatilhos da classe em ordem crescente de intervalo; o último que satisfaz `cu % intervalo == 0` define o tipo. Sem gatilho → 'S'.
5. **Herança cumulativa**: S=[S], A=[S,A], B=[S,A,B], C=[S,A,B,C], D=[S,A,B,C,D]. HH/materiais do evento = soma dos itens de checklist (classe × tipos herdados). HH armazenado nas atividades é INCREMENTAL por tipo.
6. **Plano corretivo** (oficina, mês m 0-based):
   `ratio = corr / max(0.01, prev)`
   `defl_fator = 1 − (deflator/100) × (m/11 + 0.5) × 0.5`
   `hh_corr[m] = max(0, hh_prev[m] × ratio × defl_fator × sazonal[m])`
7. **Disponibilidade**: `disp[of][m] = n_pessoas_ativas(of) × dias_uteis[m] × liquidas(of)`.
8. **Custo/hora pessoa**: `custo_mensal = sal × (1+enc/100)`; `custo_hora = custo_mensal / (média_dias_uteis × liquidas(oficina))`.
9. **Saving**: `baseline[m] = hh_prev[m] × ratio × sazonal[m]` (sem deflator); `saving_rs[m] = (baseline[m] − hh_corr[m]) × custo_hh_medio(of)`.
10. **Agenda**: eventos por ativo ordenados por data; data = dias úteis da semana em round-robin (contador por semana); oficina principal = maior HH na herança; responsável = round-robin das pessoas ativas da oficina (sem pessoas → "Equipe {oficina}").

## Fixtures de regressão (obrigatórios em CI)

**Dataset demo** (protótipo, 13 ativos): validar contra o app v4.2. Fixture
implementado em `apps/motor/tests/test_fixture_demo.py`.

**Dataset Petribú** (`make seed-petribu`, 384 ativos, premissas 06/07/2026):
tolerâncias abaixo são as normativas (únicas exigidas em CI):
- preventivas/ano = 2.101 ± 1
- HH preventiva/ano = 7.984 ± 0,1%
- HH corretiva/ano = 22.761 ± 0,1%
- eventos dez–mar = 1.025–1.026
- sazonal = [1.24,1.20,1.09,0.69,0.50,0.36,0.46,1.06,1.25,1.42,1.40,1.33]
- 1ª preventiva: colhedoras Rev. S na semana 3 (set/2026)

Números complementares verificados executando `referencias/agrovector_manutencao_Petribu_v1.0_2026-07-06.html`
em Node.js sobre os dados reais do arquivo (2026-07-16): S 1.140 · A 642 ·
B 312 · C 8 · D 0 (total 2.102); mai = 20 · set = 19 — ligeiramente
diferentes dos citados antes desta verificação (A 641, set 16), por conta
do método de contagem (data real do evento na Agenda, que pode cair no mês
seguinte ao da semana de disparo, em vez do mês da semana). Fixture
implementado em `apps/motor/tests/test_fixture_petribu.py`.

## Procedimento para alterar o motor
1. Confirmar aprovação do Fabio e atualizar `SPEC_Funcional.md §3`.
2. Escrever o teste esperado ANTES da mudança.
3. Rodar toda a suíte de regressão; se números de referência mudarem legitimamente, registrar novo baseline no fixture com justificativa no PR.
