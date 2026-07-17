# Lab 2026-07-16-1708 — DatasetH S0–S3: semântica e vínculos

**Status**: concluído como evidência sintética; protótipo dirty, sem weld.  
**Ticket de execução**: [T-EXP-DATASETH-S0-S3](../../../../tickets/T-EXP-DATASETH-S0-S3.md)  
**Contrato/oráculo**: [T-STUDY-DATASETH-COMPLETE-SEMANTICS](../../../../tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md)  
**Álgebra de vínculos**: [T-STUDY-HIERARCHY-LINK-ALGEBRA](../../../../tickets/T-STUDY-HIERARCHY-LINK-ALGEBRA.md)  
**Hipóteses**: `H-DATASETH-COMPLETE-01`, `H-HIER-LINK-ALGEBRA-01` e `H-HIER-BOUNDARY-EMPTY-01` em [roadmap-hipoteses.md](../notas/roadmap-hipoteses.md).

## Pergunta

É possível fechar a capacidade semântica de JSON antes de decidir a representação física da hierarquia, usando um IR único no qual `counts`, `offsets`, `parent-index` e `steps` sejam portadores equivalentes do vínculo?

## Escopo S0–S3

- **S0**: contrato JSON estrito e corpus de falsificação.
- **S1**: codec-oráculo explícito em preorder, completo mas deliberadamente não otimizado.
- **S2**: IR lógico de nós, arestas ordenadas e lanes de valores, independente da fonte e do wire.
- **S3**: conversões e validação da álgebra dos vínculos.

O lab não importa `src/tcf`. Os arquivos `.tcf` usam magic `#PROTO.DATASETH.S1`: são wire de pesquisa, não `#TCF.8H` canônico.

## Fluxo e artefatos

```text
inputs/01-corpus-json-completo.json
  -> model.py (DatasetH)
  -> oracle.py
  -> outputs/01..20-*.tcf
  -> decode
  -> outputs/21-corpus.roundtrip.json

DatasetH -> ir.py -> intermediates/02-ir-logico.json
                   -> intermediates/03-formas-de-vinculo.json
```

- `inputs/`: corpus e contraprova de duplicate key, com extensões reais.
- `intermediates/01-corpus-canonico.json`: referência byte a byte do round-trip.
- `intermediates/02-ir-logico.json`: nós, arestas e lanes por caso.
- `intermediates/03-formas-de-vinculo.json`: counts, offsets, parent-index e steps.
- `outputs/01..20-*.tcf`: um wire inspecionável por raiz independente.
- `outputs/21-corpus.roundtrip.json`: deve ser byte-idêntico ao canônico.
- `outputs/22-bytes.csv`: observação de tamanho, sem alegação de otimização.
- `outputs/23-contraprovas.txt`: duplicate keys, não-finitos, ciclo, profundidade, wire malformado e fronteira lossy.
- `outputs/24-resultado.txt`: gate regenerado.

## Como rodar

```powershell
python experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/run.py
```

Dirty significa descartável, não desorganizado: qualquer protótipo formal posterior começa do contrato e dos testes, sem copiar este código.
