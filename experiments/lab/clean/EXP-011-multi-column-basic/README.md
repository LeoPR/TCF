---
title: EXP-011 — Multi-column basic (sem ordering)
type: clean-experiment
status: active
tags: [tcf, multi-column, prototype, v0.6-candidate]
created: 2026-05-17
updated: 2026-05-18
predecessor: EXP-010-tcf-delta-aware-prototype
related:
  - docs/adr/0004-multi-column-header-compacto.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
---

# EXP-011 — Multi-column basic (sem ordering)

**Data**: 2026-05-17
**Tipo**: experimento clean
**Ciclo**: v0.6 → v0.7 candidato
**Estado**: ativo
**Predecessor**: EXP-010 (single-column delta-aware prototype)

## Pergunta cientifica

Pipeline single-column do EXP-010 generaliza pra multi-column
quando aplicado **por coluna independentemente**, com header
delimitador?

Especificamente:
- Encode: aplica `encode_column` em cada coluna, agrega com
  header descrevendo bytes por coluna
- Decode: ler header, separar bodies por contagem de bytes,
  aplicar `decode_column` em cada
- RT preservado byte-canonical

## Escopo

**Inclui (basico)**:
- N colunas independentes, cada uma com seu pipeline delta-aware
- Header simples: `# COL=<name> bytes=<n>` antes de cada body
- Validacao RT byte-canonical em dataset sintetico multi-coluna

**Exclui (futuro — ver
[`../../dirty/notas/futuras-otimizacoes-formato.md`](../../dirty/notas/futuras-otimizacoes-formato.md))**:
- Ordering de colunas/linhas pra compressao (O-FMT-01..04)
- Cross-column dictionary (O-FMT-06)
- Streaming/chunked (O-FMT-08)
- Type-aware per-column pipeline choice (O-FMT-07; pacote 1 ja' faz
  per-column auto-detect, mas nao escolhe pipelines diferentes)

Multi-column basico = chamadas independentes do single-column.

## Hipotese

**H1**: Aplicar EXP-010 por coluna preserva semantica do dataset
(RT OK) E reduz bytes vs encodar tudo como uma coluna gigante
(porque cada coluna tem padroes diferentes que se beneficiam de
pipelines proprios).

**H0** (rejeitada): se RT falha OU se multi-column piora bytes
significativamente vs single-encoding, design tem bug.

## Dataset

`datasets/synthetic/D17a-multi-column-mixed.csv` (criado neste exp):
- 13 rows, 4 colunas
- `timestamp`: datetime cadencia 1m (esperado: H-DA-07 hint enabled)
- `id`: numeric ID sequencial 1000..1012 (esperado: H-DA-07 hint enabled)
- `email`: emails diversos (esperado: nao detecta cadencia)
- `categoria`: A/B/C (esperado: pouca compressao, alta repetição)

Comparativo:
- **Single-encoding**: concatena tudo em 1 coluna (`linha1c1,linha1c2,...`)
- **Multi-encoding**: este EXP

## Formato do header (revisado 2026-05-17 pos critica do user)

Seguindo convencao shebang TCF (v0.5 `#TCF.5 SRDM`) — formato
compacto, sem descricoes livres, byte-precise:

```
#TCF6 M
# <size1>=<name1>,<size2>=<name2>,...
<body1 size1 bytes><body2 size2 bytes>... (concatenado sem delimitador)
```

**Princ-ipios aplicados** (cf.
[`../../dirty/notas/futuras-otimizacoes-formato.md`](../../dirty/notas/futuras-otimizacoes-formato.md)):
- Magic line estilo shebang (`#TCF6` = 5 bytes)
- Flag `M` indica multi-column (sem flag = single-column)
- Meta line: pares `size=name` separados por virgula (compacto)
- Bodies concatenados sem delimitador (sizes garantem separacao)
- Sem texto livre, sem defaults explicitos, sem redundancia

**Why byte-precise concat (nao delimitador)**: HCC body pode comecar
linhas com `#` (literais que tem `#` em raw data nao sao escapados),
entao delimitador `# ...` poderia colidir. Byte-count evita.

**Restricoes assumidas**:
- Nomes de coluna nao contem `,` ou `=` (datasets comuns OK; se
  precisar, encoding/escaping futuro)
- Single-column NAO emite shebang (compatibilidade com EXP-010);
  apenas multi-column usa header. Decisao de uniformizar (todo
  arquivo com shebang) fica pra revisao futura.

Decoder:
1. Ler linha 1: validar `#TCF6 M`
2. Ler linha 2: parsear `size=name` pairs
3. Apos LF, ler `size[i]` bytes pra cada body
4. `decode_column(body_i)` → rows da coluna i

## Validacao

- **RT byte-canonical**: `decode_table(encode_table(t)) == t`
- **Bytes vs single-encoding**: medir overhead/ganho
- **Por coluna**: cadence_detected correto? hint usado?

## Limitacoes conceituais

- Single dataset sintetico (N=1)
- Real-world (Adult Census, TPC-H) **nao testado** (proximo passo)
- Nao testa interacao entre colunas (cross-column savings)
- Header e' verboso (otimizacao registrada como O-FMT-11)

## Estrutura

```
EXP-011-multi-column-basic/
├── README.md
├── multi_col.py        ← API publica (encode_table, decode_table)
├── run.py              ← validacao em D17a
├── report.md           (gerado)
└── outputs/
    ├── D17a-multi.tcf
    └── D17a-single.tcf   (concat pra comparacao)
```

## See also

- **Single-column base**: [EXP-010](../EXP-010-tcf-delta-aware-prototype/)
- **Decisao do header multi**: [ADR-0004](../../../../docs/adr/0004-multi-column-header-compacto.md)
- **Decisao do shebang**: [ADR-0001](../../../../docs/adr/0001-tcf-format-shebang.md)
- **Otimizacoes futuras**: [`futuras-otimizacoes-formato.md`](../../dirty/notas/futuras-otimizacoes-formato.md) (O-FMT-11, 11b, 13)
- **Checkpoint pos-EXP-011**: [`2026-05-18 pausa`](../../dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md) (proximo: EXP-012 real-world via shaper)
- **Dataset usado**: [D17a synthetic](../../../../datasets/synthetic/D17a-multi-column-mixed.csv)
