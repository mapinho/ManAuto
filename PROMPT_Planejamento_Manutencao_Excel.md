# Prompt de Continuidade — Planejamento de Manutenção AgroVector (Excel funcional + App v4.2)

**Como usar:** copie o bloco abaixo e cole no início de uma nova conversa com o Claude, com a pasta "APP Manutenção" conectada.

---

## PROMPT (copiar daqui para baixo)

Você está dando continuidade ao **Planejamento Integrado de Manutenção AgroVector** da Vector Consulting (consultoria focada em performance, EBITDA e redução de custos — pilares: Processos, Tecnologia e Pessoas). O objetivo é dimensionar recursos de manutenção (pessoas, HH, insumos, peças) aproveitando janelas agronômicas (safra/entressafra).

### Ecossistema de arquivos (pasta "APP Manutenção")

1. **`Templates_Vector/Planejamento_Manutencao_AgroVector_v4.2.xlsx`** — RÉPLICA FUNCIONAL do app em Excel (22.602 fórmulas, zero erros). É a peça central de trabalho com o cliente:
   - **Abas de entrada:** Premissas (índices prev/corr, deflator, terceiros, disponibilidade de MO, dias úteis, safra, sazonalidade, gatilhos S/A/B por classe) · Frota (30 slots) · Pessoas (40 slots, com custo mensal e custo/hora calculados) · Checklist (100 slots).
   - **Abas de resultado (só fórmulas):** Cronograma (ativo × 52 semanas, semáforo S/A/B) · Plan_Prev e Plan_Corr (HH por oficina × mês) · Disponibilidade (disp vs. necessária, saldo com semáforo) · Recursos (HC necessário vs. atual) · Insumos (demanda anual com herança) · Saving (baseline deflator=0 vs. plano, em R$) · Resumo (KPIs).
   - **Abas auxiliares (não mexer):** Semanas, Cron_Uso, Eventos (1 linha por ativo×semana), Aux_HH (HH cumulativa por classe×tipo×oficina).
   - **Motor idêntico ao app:** uso acumulado semanal dispara preventiva ao cruzar múltiplo do intervalo; tipo pelo maior gatilho divisível; herança cumulativa (B executa S+A+B); horas líquidas = (brutas − almoço − café − aberturaOS) × (1 − (abs% + férias%/12 + trein/(252×efetivas))) × produtividade%; corretiva = preventiva × (corr/prev) × deflator progressivo (1 − defl%×(m/11+0,5)×0,5) × sazonalidade mensal; saving = (HH corretiva baseline − com plano) × custo médio/HH da oficina.
   - **Simplificações documentadas:** máx. 1 preventiva por ativo/semana; tipos S/A/B (C/D podem ser adicionados); dados atuais = demo do app.
2. **`agrovector_manutencao_v4.2_2026-06-16.html`** — o app (single-file, 13 abas, estado em localStorage `av_f2demo`, importadores CSV). Ver PROMPT_Desenvolvimento_App_AgroVector_v4.2.md para detalhes da arquitetura.
3. **`Templates_Vector/Parametrizacao_AgroVector_v4.2.xlsx`** — ponte para a carga: abas Frota/Pessoas/Checklist no formato exato dos importadores CSV do app.
4. **`Templates_Vector/Diagnostico_AgroVector_Manutencao_F1F2_CoresFabio.xlsx`** — diagnóstico de maturidade aplicado antes da implantação.
5. **`CLAUDE.md`** — padrões obrigatórios (lido automaticamente).

### Fluxo de trabalho com o cliente

Diagnóstico (xlsx F1F2) → coleta de dados (templates) → **parametrização e simulação na planilha de Planejamento** → validação com o cliente → carga no app (Parametrizacao → CSV → importadores) → gestão contínua no app.

### Padrões obrigatórios

- **Cores Fabio:** VERDE #00FF00 (OK) · AMARELO #FFFF00 (atenção) · VERMELHO #FF3300 (crítico, **sempre fonte branca #FFFFFF**). Verde/amarelo → fonte preta.
- **Identidade Vector:** azul marinho #1F3060 e cinza #B2B5B7.
- **Gráficos:** sempre com rótulos de dados; pizza/rosca obrigatoriamente em %.
- **Excel:** zero erros de fórmula; nunca substituir fórmulas por valores fixos; rodar recálculo e validar totais contra caso de teste conhecido antes de entregar.

### Sua tarefa
Dar continuidade a partir dos próximos passos abaixo. Confirme a prioridade com o solicitante e proponha o plano antes de alterar arquivos.

---

## O QUE FALTA FAZER (próximos passos)

1. **Validar com dados reais** — substituir os dados demo por frota, pessoas e checklists de um cliente piloto; conferir HH, headcount e saving contra o plano atual do cliente.
2. **Calibrar premissas com histórico** — usar histórico de OS real para ajustar % corretiva, sazonalidade mensal e deflator por oficina.
3. **Tipos C e D** — estender gatilhos, Aux_HH e fórmulas do Cronograma quando o cliente usar revisões C/D.
4. **Expandir capacidade** — se a frota exceder 30 ativos (ou 40 pessoas / 100 atividades), gerar nova versão com mais slots.
5. **Gráficos gerenciais na planilha** — Disponibilidade (disp vs. necessária), Saving mensal e rosca de distribuição de HH por oficina (regras: rótulos sempre, rosca em %).
6. **Módulo de cenários** — duplicar conjunto de premissas para comparar cenários lado a lado (preventiva +10%, deflator maior, renovação de frota) com Δ de saving e headcount.
7. **Carga no app validada** — gerar CSVs da Parametrizacao a partir dos dados aprovados na planilha e testar a importação completa no app.
8. **Relatório executivo** — PPT/PDF do plano anual para o sponsor (identidade Vector + cores Fabio).
9. **Evoluções do app** — ver roadmap próprio em PROMPT_Desenvolvimento_App_AgroVector_v4.2.md (multi-filial, backend, mobile, cenários no app).
