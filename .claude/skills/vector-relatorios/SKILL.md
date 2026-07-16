---
name: vector-relatorios
description: Padrões Vector para relatórios, gráficos, exportação Excel e PPT (identidade visual, cores Fabio, regras de rótulos). Usar ao criar qualquer tela com gráfico, dashboard, exportação Excel/PPT/PDF ou formatação condicional.
---

# Relatórios e identidade visual Vector

## Identidade
- Azul marinho Vector: `#1F3060` (cabeçalhos, títulos, botões primários).
- Cinza Vector: `#B2B5B7` (texto secundário, bordas).
- Fundo claro de apoio: `#E8ECF2`.

## Cores Fabio (semáforo) — REGRA OBRIGATÓRIA
- VERDE `#00FF00` = aderente/OK/superávit (score 3,5–5,0 · "Tem" · prioridade Baixa · Concluído).
- AMARELO `#FFFF00` = atenção/estimativa/gap relevante (score 2,0–3,4 · "Parcial" · Média · Em andamento).
- VERMELHO `#FF3300` = crítico/déficit (score 0–1,9 · "Não tem" · Alta · Não iniciado).
- **Preenchimento vermelho → fonte BRANCA (#FFFFFF), SEMPRE. Verde e amarelo → fonte preta.**
- Cronograma/agenda de preventivas: S verde · A amarelo · B/C vermelho (fonte branca no vermelho).

## Regras de gráficos (todas as saídas: web, Excel, PPT)
- TODO gráfico com rótulos de dados visíveis.
- Pizza e rosca: rótulos OBRIGATORIAMENTE em percentual (%).
- Eixos e títulos em pt-BR; números formato brasileiro (1.234,5).
- Web: ECharts com `label.show=true`; deficit/superávit usa cores Fabio.

## Exportação Excel (openpyxl) — paridade com a planilha v1.3
- Estrutura de abas: Menu (hyperlinks + status semáforo) → entradas → resultados → auxiliares (tabColor cinza).
- Cabeçalhos: fundo #1F3060, fonte branca bold; blocos de rótulo com fundo #E8ECF2.
- Semáforos via FORMATAÇÃO CONDICIONAL (FormulaRule), nunca pintura manual; regra vermelha com `font=branca bold`.
- Células de estimativa/pendência: fundo amarelo.
- Zero erros de fórmula (recalcular e validar antes de entregar); preservar fórmulas vivas (não valores).
- Todo arquivo com aba "Leia-me" (instruções, o que validar, pendências) e link ⌂ MENU nas abas.

## Exportação PPT (python-pptx)
- Capa: VECTOR CONSULTING (cinza) + título navy + subtítulo + rodapé "Processos · Tecnologia · Pessoas · www.vectorconsulting.com.br".
- Tabelas: cabeçalho navy/branco; status com cores Fabio (vermelho → texto branco).
- KPIs executivos primeiro (saving, headcount, aderência), detalhe depois.

## Checklist antes de entregar qualquer relatório
1. Vermelho com fonte branca? 2. Gráficos com rótulos (rosca em %)? 3. Números pt-BR? 4. Zero erros de fórmula? 5. Fonte dos dados e data no rodapé?
