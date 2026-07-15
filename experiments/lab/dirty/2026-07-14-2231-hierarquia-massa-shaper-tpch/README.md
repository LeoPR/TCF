# Lab 2026-07-14-2231 — teste EM MASSA da hierarquia com DADO REAL (TPC-H aninhado via FK)

**Status**: teste-de-capacidade/robustez, dado real. **Ticket**:
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md).

Owner (2026-07-14): *"depois precisamos de um teste em massa disso, nem que o esquema hierárquico
venha do shaper montando pra gente nosso dataset de teste."* O fuzz sintético
([lab 2120](../2026-07-14-2120-hierarquia-massa-classe-coberta/)) cobre a FORMA; aqui é **dado
REAL em massa**, aninhado pela FK do TPC-H.

## O que roda

`build.py` lê `Z:/tcf-data/interim/tpch-sf001.db` e **aninha** pela FK (o shaper achata via
`join.py`; isto é o INVERSO — normalizado → aninhado). Duas formas reais:

- `customer → [pedidos] → [itens]` (1:N em 2 níveis) — 1500 docs, 60175 itens no fundo.
- `orders → [itens]` (1:N, 1 nível, pai diferente) — 15000 docs.

**Gate** por forma: RT byte-exato `decode(encode_hierarchical(docs)) == docs` · invariante estrutural
(nº de filhos aninhados preservado) · byte-determinismo (encode 2×). Classe coberta = all-string
(`str()` em toda folha; tipos/null = camada ortogonal, pro fim). Ver
[inputs/datasets-provenance.md](inputs/datasets-provenance.md).

## Estrutura (convenção lab)

- `inputs/datasets-provenance.md` — fonte (hub Z:) + regra de aninhamento + coerção.
- `intermediates/01-nested-sample.json` — amostra (3 clientes) aninhada, diffável.
- `outputs/01-sample.tcf` — a amostra codificada (wire `#TCF.8H`).
- `outputs/02-roundtrip-sample.json` — decode da amostra (byte-idêntico ao intermediate; assert no build).
- `outputs/03-massa-result.txt` — relatório do gate em massa (as 2 formas completas).

Rodar: `python experiments/lab/dirty/2026-07-14-2231-hierarquia-massa-shaper-tpch/build.py`.
Zero mudança em `src/tcf`. Ver [result.md](result.md).
