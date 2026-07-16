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
- `unidade` do gatilho: 'H' (horas) ou 'KM' — o ativo herda da classe mas pode sobrescrever.
- HH das atividades de checklist é INCREMENTAL por tipo (herança soma).
- Salário/encargos: acesso restrito (permissão própria + criptografia pgcrypto).

## Formatos de importação (templates Vector — ordem de colunas é contrato)
- **Frota**: Nome, Classe, Modelo, Fabricante, Ano, Filial, Status, Tipo Gatilho (Horas/KM), Uso Atual, Uso Médio Mensal, Intervalo Preventiva, Garantia (true/false).
- **Pessoas**: Nome, Cargo, Oficina, Turno, Salario, Encargos%, Status.
- **Checklist**: Checklist, Tipo Prev, Classe, Oficina, Atividade, Cargo, Tipo Ativ, HH, Insumo, Qtd Insumo, Un Insumo, Peca, Qtd Peca.
- **Histórico OS**: id_os, id_ativo, data_abertura, data_fechamento, tipo_os, oficina, sistema_falha, descricao_falha, custo_total, hh_executadas, horimetro/hodometro.
- Primeira linha = cabeçalho (ignorar); encoding UTF-8 com BOM; aceitar vírgula decimal pt-BR.
- Import SEMPRE em job (Procrastinate) com relatório de erros linha a linha (não abortar na primeira falha; rejeitar linha inválida e seguir).

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
