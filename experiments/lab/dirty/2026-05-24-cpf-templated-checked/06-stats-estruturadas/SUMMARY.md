# Sub-exp 06 — NatureApplyStats SUMMARY (ISO/IEC 25012)

Estatisticas estruturadas por dataset, alinhadas a framework
academico (ISO/IEC 25012 dimensions + Kim et al. 2003 taxonomy).

## Tabela cross-dataset

| Dataset | n | apply | accuracy | complete | consist | comply | confid | RT |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| D-CPF-uniform | 1000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | OK |
| D-CPF-clustered | 1000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | OK |
| D-CPF-mixed | 1000 | 0.5000 | 0.5000 | 1.0000 | 0.5000 | 0.5000 | 0.5000 | OK |
| D-CPF-corrupt | 1000 | 0.9560 | 0.9560 | 1.0000 | 0.9560 | 0.9560 | 0.9560 | OK |
| D-CPF-edge-single | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | OK |
| D-CPF-edge-allsame | 1000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | OK |
| D-CPF-edge-allcorrupt | 1000 | 0.0000 | 0.0000 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | OK |
| D-CPF-extra-large10k | 10000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | OK |
| D-CPF-extra-hostile | 1000 | 0.2500 | 0.2500 | 0.7500 | 0.3120 | 0.2500 | 0.2188 | OK |

## Interpretacao (mapeamento literatura)

- **apply_rate alto + accuracy alto** (uniform/clustered/extra-large10k):
  dataset 'happy path' (Myers equivalence class). Encoder aplica em massa.
- **apply_rate baixo + accuracy baixo** (edge-allcorrupt/extra-hostile):
  dataset adversarial/fuzz (Miller 1990). Encoder fallback em massa,
  bytes nao compensam — heuristica de aplicacao deveria rejeitar nature aqui.
- **mixed**: 2 equivalence classes coexistindo (Rahm & Do multi-source).
  apply_rate ~0.5, consistency baixa.
- **corrupt**: mutation testing (DeMillo) com 4 tipos sistematicos.
  fallback_reasons mostra distribuicao das mutacoes.
- **edge-allsame**: cardinalidade=1 boundary (Beizer). Stats validos mas
  ratio TCF (RLE HCC) eh quem brilha — stats sozinhas nao capturam.

## Heuristica de aplicacao proposta

Schema_builder Fase 3 deve ativar nature CPF apenas se:

```
apply_rate >= 0.5  AND  consistency_rate >= 0.5
```

Caso contrario, M10 puro (sem pre-tx CPF) eh melhor — sub-exp 01
demonstrou que M10 piora bytes mas mantem RT 100% sempre.

