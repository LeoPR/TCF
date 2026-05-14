# archive/ — labs de ciclos antigos

Labs cujos achados ja' foram consolidados (ou descartados) em
research-notes ou tickets. Mantidos para historia.

## Conteudo

```
archive/
  2026-05-design-v04-fase1/    Labs da fase de design v0.4 (formato textual columnar)
```

## Status

**NAO canonico para v0.6.** Material historico apenas. Para
contextualizar:

- v0.4 (≤ 2026-05): foco em formato columnar com RLE/dict/stats
  para LLM consumption. API `encode_rows(... level=2)` etc.
- v0.5 (~2026-04): experimentos LLM benchmark Q01-Q38 (em
  `clean/EXP-001..006/`).
- **v0.6** (2026-05-10 →): foco em **algoritmo de compressao de
  strings** (TCF-CORE / alg16 + Compactacao composicional).
  Trabalho ativo em `../dirty/`.

Achados consolidados de v0.4/v0.5 (quando aplicaveis) em
`docs/findings/` (Q01-Q38) — tambem material historico para
release v0.6.

## Quando usar

- Localizar bugs/armadilhas ja' encontradas em ciclos anteriores.
- Resgatar ideias antigas que podem ser **rebatizadas como
  hipoteses novas** e re-testadas no dirty v0.6 (nao importadas).
- Rastreabilidade historica.

**Nenhuma conclusao arquivada conta como evidencia viva para v0.6**.
