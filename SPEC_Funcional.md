# SPEC Funcional — AgroVector Manutenção (produto)

Versão 1.0 · 07/07/2026 · Vector Consulting
Fonte da verdade: protótipo `agrovector_manutencao_v4.2_2026-06-16.html` + instância Petribú v1.0 + planilha funcional v1.3.

## 1. Visão do produto

Plataforma SaaS de **planejamento integrado de manutenção para o agronegócio** (garagens de usina): dimensiona HH, headcount, insumos e custo a partir de premissas, frota, pessoas e checklists, aproveitando janelas agronômicas (safra/entressafra). Diferencial: motor de cálculo que converte gatilhos de preventiva em cronograma anual de 52 semanas, plano de corretivas calibrado por histórico e saving financeiro (EBITDA).

Usuários: consultor Vector (implantação e cenários), gerente de manutenção do cliente (gestão do plano), PCM/programador (agenda semanal), diretoria (dashboards executivos). Gestão dos usuários somente
pelos admin e consultores Vector.

Autenticação (allauth): login por email, senha padrão Django ou autenticação por
rede social Google/Microsoft ou SSO.

Autorização (allauth): uma vez autenticado, a autorização se dá conforme o papel do usuário autenticado. Usuários não cadastrados não são autorizado.

## 2. Módulos (paridade com o protótipo v4.2 — 13 telas)

| # | Módulo | Descrição funcional | Regras-chave |
|---|--------|--------------------|--------------|
| 1 | Premissas | Índices por oficina (%prev, %corr, deflator a.a., % terceiros), disponibilidade de MO (8 parâmetros), dias úteis/mês, datas de safra, fator sazonal mensal, gatilhos por classe (S/A/B/C/D em horas ou km), herança cumulativa | Check %prev+%corr=100; edição recalcula todo o plano |
| 2 | Frota | CRUD de ativos: classe, modelo, ano, setor/filial, status, tipo de gatilho (h/km), uso atual (horímetro), uso semanal safra/entressafra, intervalo, garantia | Só status "Ativo" entra no plano; import CSV/XLSX |
| 3 | Pessoas | CRUD equipe: cargo, oficina, turno, salário, encargos, status | Custo mensal = sal×(1+enc%); custo/hora = custo mensal ÷ (dias úteis médios × horas líquidas da oficina) |
| 4 | Checklist | Atividades por classe × tipo de preventiva: HH, cargo executor, oficina executora, insumos e peças com quantidades | HH incremental por tipo; herança soma S⊂A⊂B⊂C⊂D |
| 5 | Cronograma | Grade ativo × 52 semanas com tipo de preventiva disparada | Ver motor §3 |
| 6 | Agenda | Preventivas em datas reais (dias úteis), oficina principal e mecânico responsável (round-robin), navegação por trimestre, visão calendário | Oficina principal = maior HH na herança; contador por semana distribui nos dias úteis |
| 7 | Plan. Preventivas | HH preventiva por oficina × mês | Soma dos itens de checklist (com herança) dos eventos do mês |
| 8 | Plan. Corretivas | HH corretiva esperada por oficina × mês | Ver motor §3.4 |
| 9 | Disponibilidade | HH disponível vs. necessária, saldo com semáforo | disp = pessoas ativas × dias úteis × horas líquidas |
| 10 | Recursos | Headcount necessário vs. atual por oficina × mês | HC nec = HH demanda ÷ (dias úteis × horas líquidas) |
| 11 | Insumos & Peças | Demanda anual = qtd por atividade × execuções (com herança) | Vínculo item→atividade obrigatório |
| 12 | Saving | Corretiva baseline (deflator=0) vs. com plano, valorizada por custo/HH | Argumento de EBITDA |
| 13 | Resumo | KPIs executivos consolidados | Tempo real |

## 3. Motor de cálculo (regras normativas — NÃO alterar sem aprovação)

### 3.1 Horas líquidas/dia por oficina
`efetivas = max(0, hBrutas − almoço − café − aberturaOS)`
`fA = abs% + férias%/12 + trein_h_ano/(252 × efetivas)`
`líquidas = efetivas × (1 − min(fA, 0.99)) × produtividade%`

### 3.2 Cronograma semanal (por ativo)
52 semanas a partir de `inicioSafra`. Semana é safra se `inicio ≤ data ≤ fimSafra`.
`usoSemana = usoMedSafra se safra senão usoMedEnt` (unidade do gatilho).
Dispara preventiva quando `floor(usoAcum+uso / itv) > floor(usoAcum / itv)`; pode haver mais de um cruzamento por semana (n = nF−nI eventos).
Tipo do evento em `cu = n×itv`: percorre os gatilhos em ordem crescente; o ÚLTIMO intervalo que divide `cu` define o tipo (ex.: itv 250/500/1000 → 6.000h = B).

### 3.3 Herança cumulativa
`S=[S] · A=[S,A] · B=[S,A,B] · C=[S,A,B,C] · D=[S,A,B,C,D]`. HH e materiais de um evento tipo T = soma dos itens de checklist de todos os tipos herdados.

### 3.4 Plano de corretivas (por oficina × mês m, 0-based)
`ratio = corr% / max(0.01, prev%)`
`deflFator = 1 − (deflator%/100) × (m/11 + 0.5) × 0.5`  (progressivo no ano)
`HHcorr[m] = max(0, HHprev[m] × ratio × deflFator × sazonal[m])`

### 3.5 Saving
`baseline[m] = HHprev[m] × ratio × sazonal[m]` (deflator = 0)
`saving_R$[m] = (baseline[m] − HHcorr[m]) × custoHH_médio_oficina`

### 3.6 Fixtures de regressão (dados Petribú 06/07/2026 — testes automatizados DEVEM reproduzir)
384 ativos → **2.101–2.102 preventivas/ano** (S 1.140 · A 641 · B 312 · C 8), **7.984 HH prev/ano** (±0,1%), **22.761 HH corr/ano** (±0,1%), pico dez–mar = 1.025–1.026 eventos, janelas: mai=20, set=16. Sazonalidade Petribú: [1.24,1.20,1.09,0.69,0.50,0.36,0.46,1.06,1.25,1.42,1.40,1.33].

## 4. Requisitos além do protótipo (produção)

- **Multi-tenant**: N clientes (usinas), isolamento por organização; papéis: admin Vector, consultor, gestor cliente, PCM, leitura.
- **Multi-filial/oficinas configuráveis** (protótipo tem oficinas fixas).
- **Apontamento de execução**: baixa de preventiva (realizada/reprogramada), % aderência plano × realizado.
- **Import**: CSV/XLSX de frota, pessoas, checklists, histórico de OS e materiais (formatos dos templates Vector); relatório de erros de carga.
- **Calibração por histórico**: sazonalidade e mix prev/corr calculados das OS importadas (como feito para Petribú).
- **Cenários**: clonar conjunto de premissas, comparar lado a lado (Δ HH, headcount, saving).
- **Exportações**: Excel do plano anual (padrão planilha v1.3), PPT/PDF executivo.
- **Auditoria**: log de alterações de premissas (quem/quando/antes/depois).
- **Offline-first não requerido**; responsivo sim (protótipo mobile v1.1 como referência).

## 5. Padrões visuais obrigatórios (Vector)
Identidade: azul #1F3060, cinza #B2B5B7. Semáforo "cores Fabio": verde #00FF00, amarelo #FFFF00, vermelho #FF3300 — **preenchimento vermelho sempre com fonte branca**. Todo gráfico com rótulos de dados; pizza/rosca obrigatoriamente em %. Cronograma: S verde, A amarelo, B/C vermelho.

## 6. Roadmap de releases
- **R1 (MVP)**: módulos 1–7 + 9 + auth multi-tenant + import frota/pessoas/checklist + fixtures Petribú passando.
- **R2**: módulos 8, 10–13 + calibração por OS + export Excel.
- **R3**: apontamento de execução + aderência + cenários + PPT executivo.
- **R4**: mobile PWA + notificações (agenda da semana por oficina/mecânico).
