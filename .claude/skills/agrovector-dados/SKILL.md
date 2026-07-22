---
name: agrovector-dados
description: Modelo de dados AgroVector, importadores CSV/XLSX (templates Vector) e calibração por histórico de OS. Usar ao criar/alterar models, migrations, seeds, importadores ou cargas de dados de clientes (frota, pessoas, checklists, gatilhos, OS, materiais).
---

# Dados e importação — AgroVector

## Modelo de dados (núcleo)
Ver `SPEC_Tecnica_Ambiente.md §3`. Entidades: Organizacao > Filial > Setor · Oficina (índices + disp_mo JSONB) · ClasseAtivo > Gatilho (S..D) · Ativo (+ MedicaoUso) · Pessoa · ChecklistAtividade (+ AtividadeMaterial) · ItemMaterial · ConjuntoPremissas (versionado, JSONB calendário) > PlanoAnual > EventoPreventiva · OrdemServico (histórico).

Regras:
- Tudo é multi-tenant: FK `organizacao` + manager `for_org()` obrigatório.
- Oficinas e classes são CONFIGURÁVEIS (nunca hardcodar nomes).
- `unidade` do gatilho/ativo: `Horas` ou `KM` (convenção do motor, `apps/motor/tipos.py`)
  — o ativo herda da classe mas pode sobrescrever. O importador de Frota recebe `H`/`KM`
  (convenção do template_frota.xlsx) e mapeia para `Horas`/`KM` na carga.
- HH das atividades de checklist é INCREMENTAL por tipo (herança soma).
- Salário/encargos: acesso restrito (permissão própria + criptografia pgcrypto).

## Formatos de importação (templates Vector — ordem de colunas é contrato)
Existem DOIS formatos no repo, não confundir:
- `Templates_Vector/Parametrizacao_AgroVector_v4.2.xlsx` — formato simples do CSV nativo do
  **protótipo** (Nome/Classe/Modelo/...). Sem IDs estáveis; premissas/gatilhos ali são
  para digitação manual na aba Premissas do app, não têm importador de arquivo.
- `Templates_Vector/template_*.xlsx` — **os importadores reais do produto** (implementados em
  `apps/importacao/importadores/`), com chaves externas estáveis (id_ativo,
  id_funcionario, id_checklist/id_atividade, id_item, id_os) para permitir reimportação
  (upsert) e reconciliação. É este o formato que vale como contrato.

Colunas de `template_*.xlsx` (ordem é contrato, implementado 1:1):
- **Frota**: id_ativo, descricao, classe, subclasse, ano_fabricacao, placa_serie, filial,
  centro_manutencao, oficina, unidade_medicao (`H`/`KM` — diferente da convenção
  `Horas`/`KM` do motor; o importador faz o mapeamento), hodometro_atual,
  uso_medio_mensal, tipo_preventiva_atual, ultima_prev_data, ultima_prev_medicao, status.
  Sem uso_sem_safra/uso_sem_entressafra: o importador divide uso_medio_mensal
  igualmente pelas ~4,345 semanas do mês como aproximação inicial.
- **Pessoas**: id_funcionario, nome, cargo, tipo_mo, oficina, centro_manutencao, filial,
  salario_base, encargos_pct, turno, horas_contratuais_dia, status.
- **Checklist**: id_checklist, nome_checklist, tipo_preventiva, classe_ativo, oficina,
  seq, id_atividade, descricao_atividade, tipo_atividade, hh, tipo_mo, observacao.
  **A chave natural é (id_checklist, id_atividade), NUNCA só id_atividade** — o mesmo
  id_atividade (ex.: "troca de óleo") se repete em vários checklists porque a
  herança cumulativa (S⊂A⊂B) faz o mesmo item aparecer nas revisões A e B.
- **Catálogo de itens**: id_item, descricao_item, tipo_item, subtipo, unidade,
  custo_unitario, moeda, estoque_minimo, estoque_atual, fornecedor_principal,
  codigo_fabricante, codigo_interno_erp, aplicacao_classe, observacao. Campos de
  estoque/moeda/ERP não são persistidos (fora do escopo do produto). Insumo x Peça é
  inferido pelo prefixo de id_item (`INS-`/`PEC-`), com fallback no texto de tipo_item.
- **Peças/insumos do checklist**: id_checklist, id_atividade, id_item, descricao_item,
  tipo_item, unidade, quantidade, custo_unitario, fornecedor_preferencial,
  codigo_fabricante. Vincula por (id_checklist, id_atividade) + id_item — exige
  Checklist e Catálogo de itens já importados.
- **Histórico OS**: id_os, id_ativo, data_abertura, data_fechamento, tipo_os, oficina,
  sistema_falha, descricao_falha, hh_executadas, tipo_mo, custo_hh, custo_pecas,
  custo_total, mecanico_responsavel, medicao_na_os. Só id_os/data_abertura/tipo_os são
  obrigatórios — ativo/oficina não encontrados viram `None`, não rejeitam a linha (a OS
  ainda serve para calibração sem o vínculo).
- Oficina e Classe (e seus Gatilhos) precisam existir previamente no cadastro — o
  importador rejeita a linha se não encontrar (nunca inventa índices/gatilhos). Filial e
  Centro de Manutenção (→ `core.Setor`) são criados automaticamente por não terem
  configuração própria.
- Primeira linha = cabeçalho; aceita CSV (UTF-8 com/sem BOM) e XLSX; aceita decimal com
  ponto OU vírgula pt-BR (dados reais chegam nos dois formatos, às vezes como número,
  às vezes como texto).
- Import SEMPRE em job (Procrastinate, `apps/importacao/tasks.py`) a partir de uma view —
  nunca síncrono num request. `manage.py importar --tipo <tipo> --org <slug> --arquivo
  <caminho>` roda síncrono, apropriado só para CLI/ops. Relatório de erros linha a linha
  (não abortar na primeira falha; rejeitar linha inválida e seguir).

### Armadilhas reais encontradas implementando os importadores
- `Model.objects.for_org(org).get_or_create(**kwargs)` **não propaga** `organizacao` para
  a criação — `for_org()` só filtra a busca; se `organizacao` não estiver entre os
  kwargs passados ao `get_or_create`, a criação falha com `organizacao_id` nulo. Sempre
  passar `organizacao=organizacao` explicitamente nos kwargs do `get_or_create`/
  `update_or_create`, nunca confiar no `.filter()` encadeado.
- Mojibake real (`agrovector-dados`) usa **CP1252**, não Latin-1/ISO-8859-1: são o mesmo
  na faixa ASCII e em grande parte da faixa acentuada, mas divergem em 0x80–0x9F (aspas
  curvas, travessão) — um arquivo real tinha "Ó" corrompido usando exatamente essa
  faixa, e a correção com Latin-1 falhava silenciosamente (round-trip não fechava) e
  deixava o mojibake sem corrigir. Ver `apps/importacao/parsing.py:normalizar_mojibake`.

## Calibração por histórico de OS (como feito para Petribú)
1. Classificar tipo_os em PREV (Preventiva, Lavagem/Inspeção/Lubrificação, Preditiva, Paradas programadas/oportunidade) × CORR (Corretiva, Falha operacional).
2. Mix por oficina: `prev% = n_PREV/(n_PREV+n_CORR)` (por contagem; evoluir para HH/custo quando disponível).
3. Sazonalidade: contagem de CORR por mês ÷ média mensal, arredondar 2 casas (média = 1.0).
4. Inferir janela de safra pelos meses com fator > 1.
5. Dados sujos conhecidos: hh_executadas frequentemente 0%; custo_total pode ter significado inconsistente (validar com cliente antes de usar em saving); horímetros zerados; encoding mojibake (Ã£ → ã) — normalizar na carga.

## Lições da carga Petribú (reaproveitar)
- Mapear Classe Operacional do cliente → ClasseAtivo do app por dicionário revisável (ex.: 'Cam. Canavieiro'→Caminhão, 'Carreg. Bell'→Carregadeira/Pesada).
- Definir escopo: excluir irrigação, motos, motores estacionários do plano de garagem (registrar exclusões).
- Frota mestre: reconciliar múltiplas fontes (inventário × relação × cadastro) e aplicar lista de vendidos/mantidos.
- Sempre gravar a fonte e a data da carga (`origem_arquivo`, `carregado_em`).
