---
title: T-STUDY-DATASETH-COMPLETE-SEMANTICS — fechar semântica hierárquica antes do wire
status: in-progress
priority: P1
created: 2026-07-16
updated: 2026-07-16
blocked-by: []
related:
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/T-EXP-DATASETH-S0-S3.md
  - experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md (mesmo território, 2026-07-13)
---

# T-STUDY-DATASETH-COMPLETE-SEMANTICS — fechar semântica antes do wire

**[dispositivo→pesquisa]** Este ticket separa capacidade semântica de simplificação física. JSON é o
primeiro domínio de prova; DatasetH permanece independente da fonte e o core não ganha `encode_json`.

## Hipótese

**H-DATASETH-COMPLETE-01**: um modelo recursivo fechado — objeto ordenado com nomes únicos, array
ordenado e escalares `string|integer|number|boolean|null` — mais presença explícita é suficiente para
representar qualquer valor JSON padrão sem decidir header, counts, rep-level ou organização de colunas.

Políticas do estudo:

- raiz arbitrária;
- ausência distinta de `null`, `"null"` e string vazia;
- objetos preservam ordem e rejeitam duplicate keys;
- `integer` e `number` são kinds distintos; number usa precisão decimal finita;
- igualdade é semântica, não reprodução lexical (`1.2500` pode canonicalizar para `1.25`);
- NaN e infinitos ficam fora do contrato JSON;
- ciclos e profundidade total acima do limite falham alto;
- strings aceitam Unicode e controles, inclusive newline.

## Plano

- [x] **S0** — corpus de falsificação e contrato executável.
- [x] **S1** — codec-oráculo preorder explícito, completo e não otimizado.
- [ ] Expandir corpus com documentos realistas de transmissão, sem baixar dados antes de consultar a infra.
- [ ] Firmar a política pública de precisão/identidade numérica antes do weld.
- [ ] Usar o oráculo como comparador comum de S4–S7.

## Gate S0–S1

- RT semântico de todas as formas de raiz e composições do corpus;
- round-trip JSON canônico como arquivo byte-idêntico;
- arquivos `.tcf` reais e inspecionáveis por caso;
- duplicate keys, NaN/Infinity, ciclo, profundidade e wire malformado fail-loud;
- zero import ou mudança em `src/tcf`.

## Update 2026-07-16

Lab [S0–S3](../experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/):
**20/20 RT**, **8/8 fail-loud**, 20 wires `.tcf`, corpus round-trip byte-idêntico; evidência sintética
de design. A hipótese sobre capacidade recebe `confirmada-conceitual`, confiança Média, limitada ao
contrato implementado. Continua aberta para corpus realista, política numérica pública e integração.
