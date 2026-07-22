# Lab 2026-07-17-0233 — P4b: RAIZ GENERALIZADA (J1) — estudo → weld

**Aprovação**: owner delegou os defaults com direito a veto ("pode fazer o 1->2->3").
**Status**: estudo verde → WELDED no core (mesma sessão). Fecha o **J1 do funil**.

## As 4 decisões (defaults aplicados — owner pode vetar)

1. **Escopo**: J1 INTEIRO no `.8` (todas as formas de raiz do funil).
2. **Discriminador**: `#`+kind logo após o magic, **só para raiz ≠ dataset** — a posição era
   fail-loud ("nome de campo vazio"), então: decoder antigo falha ALTO em wire novo (pré-1.0
   correto), e o DATASET (todos os wires existentes) fica **0 B / byte-idêntico**. O(1), offset
   fixo. (A opção "char sempre presente" re-pinaria tudo; o eixo "cada byte conta" do owner e o
   precedente de welds aditivos decidiram.)
3. **API**: `encode_hierarchical(data)` aceita qualquer raiz D_json; `decode` devolve o **tipo
   EXATO** da raiz (contrato do parecer: o envelope NUNCA escapa).
4. **Terminologia**: "raiz generalizada" adotada.

## A gramática

| wire | raiz | mecanismo |
|---|---|---|
| `#TCF.8H<meta>` | dataset (≥1 registro c/ campos) | **INTACTO** (byte-compat total) |
| `#TCF.8H#D<N>` | `[]` (N=0) · `[{}]`×N | contagem explícita (funil J1: "estruturas sem folhas com contagem explícita" — problema B) |
| `#TCF.8H#E` | `{}` | **DEFINIÇÃO** (H-STRUCT-DEF-01: forma opaca; o envelope não serve — campo-marcador não gera coluna) |
| `#TCF.8H#O<meta>` | objeto único não-vazio | dataset de 1, desembrulhado (canonicidade: ≠1 registro = fail-loud) |
| `#TCF.8H#V<meta>` | qualquer VALOR (escalar, `""`, null, array de escalares, array-em-array) | ENVELOPE `[{"": V}]` (campo `\z`); decode desembrulha; ≠1 campo/registro = fail-loud |

Tudo REUSA o maquinário welded (counts, masks, tags, escape) — zero gramática nova de corpo.

## Evidência

- **Estudo** (`proto.py`+`run.py`): gate do parecer + J1 **19/19** RT tipo-exato com `.tcf` +
  roundtrip byte-idêntico; byte-compat dataset **True**; adversarial **9/9** fail-loud; distinções
  `[]≠[{}]≠{}≠None≠""≠0≠False` todas de pé; fuzz **7408/7408** (592 fora-da-classe fail-loud).
- **Weld**: suíte **843 passed** · gates de bytes **49/49** (flat + navegação .8H, zero re-pin) ·
  paridade: RAIZ_LACUNAS **promovido a PARIDADE** (D_json COMPLETO, `LACUNAS = {}`).
- **Auditoria inline** (workflows fora por spend-limit): fuzz adversarial de raízes
  **14738/14738** tipo-exato (0 falhas; 5262 fora-da-classe fail-loud) · mutação de wire: 28
  fail-loud tipados; 6 aceitos-divergentes TODOS da classe indistinguível-por-construção
  (kind-swap = wire canônico de OUTRO documento; magic truncado = contrato órfão do flat) —
  registrados nas limitações inerentes do T-API-BOUNDARY-CONTRACTS.

## Custos medidos

dataset **+0 B** · objeto único **+2 B** (`#O`) · `[]` = 11 B · escalar = 19 B · null = 18 B.

## Fronteira honesta pós-J1

`{"a": {}}` (objeto único cujos campos são TODOS marcadores vazios) segue fail-loud — problema B
residual (sem coluna portadora), família O-FMT-20/registro-'0'. Lista MISTA = P5 (J2). Ordem de
chaves em ragged = decisão S6 pendente.
