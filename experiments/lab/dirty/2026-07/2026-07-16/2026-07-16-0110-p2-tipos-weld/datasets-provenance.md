# Proveniência das entradas

Metodologia do owner (didático → realista → massa). Viés declarado por etapa.

- `inputs/01-didatico-tipos.json` — **DIDÁTICO**: cada tipo escalar (int/float/misto/bool) + a
  disambiguação (campos `a`/`b` string vs `c`/`d` tipados no MESMO registro) + tipos-juntos +
  arrays tipados + number nullable + array-number-null-elemento. Bias total (força cada caso).
- `inputs/02-realista-pedidos.json` — **REALISTA**: pedidos e-commerce com `pedido` (int),
  `total`/`preco` (float), `pago`/`brinde` (bool), `cupom` null (P3a), `itens` aninhados tipados.
  Sintético-realista, plausível de API de loja.
- **MASSA** (`run.py`): fuzz seedado (`random.Random(20260716)`), colunas com stype fixo por-campo
  (string/number/bool), ~20% null nos campos, arrays tipados com ~25% null-elemento. 6000 docs.

Roundtrip diffável em `outputs/*-rt.json` (byte-idêntico ao `intermediates/*.json`, asserido no
`run.py`). Números com precisão float, big-int, negativos, -0.0 exercitados nos testes
(`tests/test_hierarchical_rt.py::test_p2_tipos_rt`).
