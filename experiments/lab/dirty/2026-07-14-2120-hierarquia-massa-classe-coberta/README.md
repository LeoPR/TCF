# Lab 2026-07-14-2120 — fuzz EM MASSA da classe coberta do weld hierárquico

**Status**: teste-de-robustez, sintético determinístico. **Ticket**:
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md).

Owner (2026-07-14): *"vamos fixar o óbvio primeiro. fechar, testar em massa e ir fechando os
outros."* O **óbvio** = o codec hierárquico weldado em `src/tcf/hierarchical.py` (commit a20ddf7),
na classe que **ele já cobre**. Este lab fecha isso com **fuzz em massa**.

## O que roda

`fuzz.py` gera, com **seed fixa (determinístico/reproduzível)**, 8000 documentos hierárquicos
aleatórios DENTRO da classe coberta e exige RT byte-exato `decode(encode_hierarchical(recs)) == recs`.

Classe COBERTA (o gerador produz): raiz = lista de objetos com **mesmo schema** (sem ragged);
escalares string; objetos `{}` (1:1); arrays `[]` de objetos ou escalares (1:N) com `#count`;
arrays VAZIOS; múltiplos arrays IRMÃOS; arrays ANINHADOS (profundidade 0–3). Escalares variados:
numérico-como-string, baixa-cardinalidade (exercita @dict/RLE), com separadores (exercita escaping),
texto livre.

Fora da classe (NÃO gerado — é fail-loud, coberto em `tests/test_hierarchical_rt.py`): ragged,
null, tipos mistos, N:N.

## Resultado

```
documentos aleatórios (seed 20260714): 8000
RT byte-exato: 8000/8000   ·   falhas: 0
cobertura: arrays vazios 5263 · >=2 arrays irmãos 2379 · aninhados 1609
```

Ver [outputs/01-fuzz.txt](outputs/01-fuzz.txt) e [result.md](result.md). Zero mudança em `src/tcf`
(usa só a API pública). Rodar: `python experiments/lab/dirty/2026-07-14-2120-hierarquia-massa-classe-coberta/fuzz.py`.
