# Resultado — 10-pacote-completo-com-validacao

**Status global**: **TODOS OK** (8/8)

## Tabela consolidada

| Dataset | Granul. | Linhas | Raw | TCF | RT staged | RT self-contained | Byte-canonical |
|---|---|---:|---:|---:|---|---|---|
| [D11a-datas-dia](D11a-datas-dia/_SUMMARY.md) | day | 12 | 136 | **42** | OK | OK | MATCH |
| [D11b-datas-borda](D11b-datas-borda/_SUMMARY.md) | day | 14 | 158 | **59** | OK | OK | MATCH |
| [D11c-datas-mensal](D11c-datas-mensal/_SUMMARY.md) | day | 13 | 147 | **22** | OK | OK | MATCH |
| [D11d-datetime-min](D11d-datetime-min/_SUMMARY.md) | second | 13 | 264 | **34** | OK | OK | MATCH |
| [D11e-datetime-mensal](D11e-datetime-mensal/_SUMMARY.md) | second | 13 | 264 | **34** | OK | OK | MATCH |
| [D11f-datetime-ms](D11f-datetime-ms/_SUMMARY.md) | ms | 13 | 316 | **39** | OK | OK | MATCH |
| [D11g-datetime-us](D11g-datetime-us/_SUMMARY.md) | us | 13 | 355 | **43** | OK | OK | MATCH |
| [D11h-datetime-ns](D11h-datetime-ns/_SUMMARY.md) | ns | 13 | 394 | **46** | OK | OK | MATCH |

## Validacao em duas vias

Cada dataset valida duas decodificacoes independentes:

1. **RT staged** (`6-decode/final.txt`): decoder usa modulos
   `decoder.py` + `stage_*.py`. Demonstra que o pipeline e'
   inversivel.

2. **RT self-contained** (`7-validation/rt-self-contained.txt`):
   `decode_self_contained()` recebe APENAS o file path do `.tcf`.
   Auto-detecta natureza pela primeira linha. Sem hint externo,
   sem D11x.csv, sem metadata sidecar. Demonstra que o arquivo
   carrega TUDO necessario.

## Estrutura de output (parcimoniosa, 7 fases por dataset)

```
outputs/<dataset>/
├── _SUMMARY.md             one-pager
├── 1-input/data.txt
├── 2-pre-tx/{A-metadata.json, B-normalized.txt, C-optimized.txt}
├── 3-obat/tokens.txt
├── 4-hcc/{trace.txt, rede.txt}
├── 5-encoded/output.tcf      (gitignored, regeneravel)
├── 6-decode/{tcf-decoded.txt, stage-C-reverse.txt, final.txt}
└── 7-validation/{rt-staged.txt, rt-self-contained.txt, byte-canonical.txt}
```

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/10-pacote-completo-com-validacao/run.py
```

Ou validacao standalone de um .tcf qualquer:

```bash
python lib/self_contained_decoder.py outputs/D11a-datas-dia/5-encoded/output.tcf
```

## Conexoes

- [`../08-granularidades-finas/`](../08-granularidades-finas/) — pipeline base
- [`../09-auditoria-self-contained-D11a/`](../09-auditoria-self-contained-D11a/) — auditoria pioneira
