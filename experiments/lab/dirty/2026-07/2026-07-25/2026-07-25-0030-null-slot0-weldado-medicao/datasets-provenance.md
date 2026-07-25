# Proveniência — null no slot 0, medição do weld (2026-07-25-0030)

**Fonte**: sintético/determinístico + os datasets **reais do gate** (D1-D9, já versionados em
`datasets/synthetic/`). Nenhum download, nenhum CPF/CNPJ.

## Casos nomeados (5) — os mesmos do lab 2026-07-24-2210, para comparabilidade direta

| id | dados | papel |
|---|---|---|
| `A-exemplo-owner` | `[null, "", "true", "false", "oi", null, "null"]` | exemplo literal do owner; as 4 vias |
| `B-n7-1null` | 7 status, 1 null | n pequeno, null único |
| `C-todos-null` | 12× null | borda: coluna 100% null |
| `D-null-bordas` | null na 1ª e na última posição | posição extrema |
| `E-sem-null` | 4 status, 0 null | **CONTROLE** de byte-identidade |

## Regimes (12)

`n ∈ {10, 100, 1000}` × densidade `∈ {1, 10, 50, 90}%`, vocabulário de 5 status realistas,
null sorteado por **LCG local com seed fixa (7)** — sem `random` não-seedado, sem relógio.

**Desvio declarado**: em `n=10`, as densidades de 1% e 10% produziram **0 nulls**. As linhas
ficaram — viraram controles extras de byte-identidade — mas **não medem o que o rótulo
sugere**. Visível na coluna `nulls` do `result.md`, e elas entram na estatística de
"colunas sem null", não na de "com null".

## Baselines

- **`antes`** = a rota que a coluna tomava **antes do weld**: `.8H` se tem null, flat se não
  tem. A 1ª rodada deste lab errava isso (forçava tudo pro `.8H`) e inflava os controles —
  corrigido e registrado no README.
- **`depois`** = `encode()` do `src/tcf` **REAL**. Não é protótipo — é o produto.
- **D1-D9** = datasets reais do gate, conferidos contra os pinos do ADR-0034. É a evidência
  de byte-neutralidade; os pinos foram fixados **antes** deste weld.

## gzip

Entra como **sinal qualitativo, não critério** (feedback `gzip-não-é-TCF`). Nível 9,
determinístico.

## Reprodutibilidade

`python run.py` regenera byte-a-byte. **Este lab não escreve em `src/tcf`** — o weld foi
feito à parte e está versionado (suíte 937 passed, gates verdes).
