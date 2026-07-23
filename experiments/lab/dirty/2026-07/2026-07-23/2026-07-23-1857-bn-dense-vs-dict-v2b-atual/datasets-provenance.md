# Proveniência — bN-dense vs dict/V2-B atual

**Origem**: adult-census REAL — `Z:/tcf-data/external/adult-census/adult.csv` (48.842 linhas), dataset
canônico do projeto. Nenhum download (regra: usar `Z:/tcf-data/`). **Amostra**: primeiras 10.000
linhas, declarada no result.md. Determinístico (sem aleatório).

**Colunas** (9 categóricas low-card, k=2..41 → w=1..8): sex, class (k=2) · race (5) · relationship (6)
· marital-status (7) · workclass (9) · occupation (15) · education (16) · native-country (41).
Valores como estão no CSV, sem limpeza.

**Comparação**: total-vs-total, ambos **self-contained**.
- Lado TCF: `encode({col: vals})` COMPLETO (header `#TCF.8M...` + dicionário + corpo), com o
  `emitted_mode` real lido de `SideOutputs` (foi `dict` em 8, `tcf` na k=41). É o que o TCF emite hoje.
- Lado protótipo: header `#PB w n <domínio>` + corpo base64 dos índices empacotados a w bits.

**Viés/limite declarado**: cada coluna foi encodada como tabela de **1 coluna** — num multi-col real o
framing amortiza diferente (o ganho de CORPO deve se manter; o TOTAL não exatamente). O protótipo NÃO
faz escaping do domínio (separador `\x1f`), então um weld real custaria alguns bytes a mais. Só bytes
são medidos — não latência/CPU.

**Sem dados sensíveis**: adult-census é público (UCI); colunas demográficas categóricas, sem PII
reconstruível nas colunas medidas.

**Reprodutibilidade**: `python run.py` regenera. RT obrigatório dos DOIS lados (`decode(wire_tcf)` e o
decoder do protótipo) — bytes só reportados com RT ✅. Wires salvos em `outputs/` para auditoria.
