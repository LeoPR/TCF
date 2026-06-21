# 10 — Pacote completo com validacao embutida (08 + 09 unificado)

**Estado**: aberto (10a iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)

## Pergunta cientifica

Repetir o experimento do sub-exp 08 (pipeline staged em 8 datasets,
day → ns), acrescentar a validacao self-contained do sub-exp 09
(decoder isolado provando que `.tcf` carrega tudo), e organizar o
output em **fases sub-segmentadas** pra inspecao limpa.

## Princípios deste sub-exp

1. **Validacao e' parte natural do output**: cada dataset gera
   `7-validation/` com 3 checks (RT staged, RT self-contained,
   byte-canonical). Sem isso, nao confiamos no algoritmo.
2. **Parcimônia em arquivos**: cada fase em sub-pasta propria, com
   1-3 arquivos cada. Sem dezenas de arquivos soltos.
3. **Auto-deducao + self-containment**: o `.tcf` carrega dados +
   refs; natureza/granularidade sao inferidas da primeira linha.
   Sem hint externo, sem JSON sidecar.

## Estrutura

```
10-pacote-completo-com-validacao/
├── README.md                          # este arquivo
├── lib/                               # codigo modular (copia de 08 + decoder standalone)
│   ├── stage_a_identify.py
│   ├── stage_b_normalize.py
│   ├── stage_c_optimize.py
│   ├── decoder.py                     # staged (modular)
│   └── self_contained_decoder.py      # isolado: recebe SO o .tcf path
├── run.py                             # orquestrador (processa 8 datasets)
├── outputs/                           # 7-fase per dataset
│   └── <D11x>/
│       ├── _SUMMARY.md                # one-pager (RT, bytes, audit)
│       ├── 1-input/data.txt
│       ├── 2-pre-tx/                  # 3 arquivos
│       │   ├── A-metadata.json
│       │   ├── B-normalized.txt
│       │   └── C-optimized.txt
│       ├── 3-obat/tokens.txt          # tokenizador alg16
│       ├── 4-hcc/                     # composicional
│       │   ├── trace.txt
│       │   └── rede.txt
│       ├── 5-encoded/output.tcf       # final .tcf (gitignored)
│       ├── 6-decode/                  # caminho de volta (staged)
│       │   ├── tcf-decoded.txt
│       │   ├── stage-C-reverse.txt
│       │   └── final.txt
│       └── 7-validation/              # checks
│           ├── rt-staged.txt
│           ├── rt-self-contained.txt
│           └── byte-canonical.txt
└── result.md                          # consolidado (gerado por run.py)
```

## Datasets

8 datasets cobrindo day → ns:

| Dataset | Granularidade | Fonte (sub-exp inicial) |
|---|---|---|
| D11a-datas-dia | day | 01 |
| D11b-datas-borda | day | 02 |
| D11c-datas-mensal | day | 03 |
| D11d-datetime-min | second | 06 |
| D11e-datetime-mensal | second | 07 |
| D11f-datetime-ms | ms | 08 |
| D11g-datetime-us | us | 08 |
| D11h-datetime-ns | ns | 08 |

## Os 3 checks de validacao por dataset

### Check 1 — RT staged (`7-validation/rt-staged.txt`)

Pipeline reverso usando os modulos canonicos:
1. `tcf.decode(.tcf)` → pre-tx output
2. `stage_c.deoptimize_scales` → stage B form
3. `stage_b.denormalize_from_unit` → linhas originais

Compara linha-a-linha com input.

### Check 2 — RT self-contained (`7-validation/rt-self-contained.txt`)

Mesma logica, mas via `decode_self_contained()` que recebe **APENAS
o path do .tcf**. Auto-detecta tudo. Sem metadata externo. Sem hint.

### Check 3 — Byte-canonical (`7-validation/byte-canonical.txt`)

Sumario: ambos os decoders produziram saida byte-canonical com input?

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/10-pacote-completo-com-validacao/run.py
```

Standalone validacao de qualquer `.tcf`:

```bash
python lib/self_contained_decoder.py <path-to-tcf>
```

## Critério de fechamento

- [ ] 8/8 datasets RT staged OK
- [ ] 8/8 datasets RT self-contained OK
- [ ] 8/8 datasets byte-canonical MATCH
- [ ] Estrutura de output limpa (7 sub-pastas por dataset, 1-3 arquivos cada)
- [ ] `_SUMMARY.md` per dataset preenchido + `result.md` top-level

## Conexoes

- [`../08-granularidades-finas/`](../08-granularidades-finas/) — pipeline base reproduzido aqui
- [`../09-auditoria-self-contained-D11a/`](../09-auditoria-self-contained-D11a/) — decoder isolado pioneiro
- [`../README.md`](../README.md) — T01 macro
