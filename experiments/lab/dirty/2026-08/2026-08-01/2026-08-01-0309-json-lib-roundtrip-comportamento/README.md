# 2026-08-01-0309 — `dataset → json lib → dataset` × `dataset → TCF → dataset`

Régua empírica pro futuro **modo-json** do TCF (param hipotético: quando o TCF preserva o
que o json perderia/rejeitaria, ele ALERTA como o json alertaria; sem o flag, faz tudo que
pode; ambíguos "fogem" pro comportamento json). 3 camadas separadas: **RFC 8259** ×
**json lib** (`json` do Python) × **dataset Python**. 29 casos, vereditos PRESERVA /
ALTERA / ERRO por rota, tipo-estrito (deep, chaves inclusas, `-0.0` por copysign).

## Os 4 grupos (+ 2 fora da malha)

- **(a) ambos preservam — 15**: tipados puros, `int × float` (`1` × `1.0`), `-0.0`, int
  gigante, vazios, unicode NFD, escalares na raiz, unicode/emoji em valor.
- **(b) json ALTERA e TCF PRESERVA — 0. VAZIO, e é o achado central**: todas as perdas da
  lib Python (coerção de chave, tuple→list, dup-key) ocorrem em casos que o TCF
  **rejeita**, não preserva.
- **(c) json aceita e TCF REJEITA — 11**: NaN/±Inf (a lib é mais permissiva que a RFC),
  união mista (o caso central do lazytype), tuple, chave não-str (a lib COAGE
  silenciosamente), str com `\n` embutido.
- **(d) ambos rejeitam — 1**: bytes.
- **⚠ fora da malha**: `chave-duplicada` (lib = last-wins silencioso; TCF não expressa) e
  **`chave-vazia` — o ÚNICO caso onde o TCF ALTERA**: `{"": ...}` volta `{"0": ...}` com
  `UserWarning` (coluna anônima). Não é silencioso, mas é perda com RT quebrado —
  **candidato a ticket**.

## Catálogo de alertas do modo-json (resumo; detalhe no result.md §2)

União mista por coluna · distinção int × float (cross-ecossistema) · int > 2^53 ·
NaN/±Inf (lib aceita, RFC rejeita) · chave não-str/tuple/dup (TCF já rejeita citando a
perda do json) · string com `\n`. Todos detectáveis de graça no pré-pass; filosofia
SideOutputs: só alerta, nunca arruma.

## Dados

`outputs/matriz.csv` (29 casos × vereditos × detalhes) · `outputs/alteracoes.json`
(before/after de cada mutação) · `outputs/knobs-nan-medidos.json` (`allow_nan` /
`parse_constant` medidos) · `intermediates/*-roundtrip-obtidos.json`.

## Rodar

```
python run.py
```

Sai `0` sempre que a matriz se materializa; o caso `chave-vazia` é achado reportado, não
falha do lab. `src/tcf` intocado.
