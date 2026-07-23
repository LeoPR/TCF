# 2026-07-23-0300 — Single-column em massa por TIPO (baseline da implicitude)

Testa a **regra de implicitude** (nota [`2026-07-23-0259`](../../../notas/2026-07/2026-07-23-0259-implicitude-singlecol-logica.md))
numa coluna única: `list`/`count`/estrutura são dedutíveis → implícitos; só o **tipo** é
irredutível. Mede o comportamento ATUAL (baseline, antes de qualquer código de core) por tipo +
specs, em **massa** (N=500), com **equivalência JSON** obrigatória.

**Refs**: nota da lógica `2026-07-23-0259` · [api.md](../../../../../../docs/reference/api.md) ·
ADR-0030 (freeze single-col) · [T-OPT-INFERENCE](../../../../../../tickets/T-OPT-INFERENCE.md).

## Estado

- **é**: baseline medida — quanto do wire é o TIPO/estrutura vs os elementos, por tipo, em massa.
- **será**: comparação contra um `single-col tipado` (desvio opt-in `#TCF.8:n`) quando/se for implementado.

## Como rodar

```
python run.py     # regenera inputs/ outputs/ + result.md · N=500 · esperado 0 falhas de equivalência
```

## Achado (ver `result.md`)

- **string = órfão, overhead 0**: `list`-ness e tipo já IMPLÍCITOS. O alvo.
- **number/bool/null (`.8H` hoje)**: overhead **FIXO ~19–28 B** (envelope `#V` + nome-vazio `\z` +
  coluna `#count` + `[]`). Domina colunas pequenas (int-repeat: 25 B de 34 = **74%**; int-seq: 26/57
  = **46%**), some nas grandes (int-rand: 28/4370 = 0.6%). Ou seja: a maquinaria hierárquica custa
  caro **exatamente quando a coluna é pequena** — que é o payload minúsculo que o owner prioriza.
- **specs**: overhead ~11–13 B (header `#TCF.8 :id`) — a nature já é uma coluna tipada.
- **equivalência JSON: 14/14 ✅** — RT do TCF == RT do JSON (mesmo objeto Python, tipos preservados).

**Leitura pro alvo**: um `single-col tipado` cortaria o overhead de ~26 B pra ~9 B (só o header do
tipo), aproximando number/bool do zero-overhead da string. Numa tabela com muitas colunas pequenas
tipadas, isso compõe.

## Layout

`inputs/<id>.json` (a lista) · `outputs/<id>.tcf` (wire real) · `outputs/<id>.roundtrip.json`
(decode, diffável) · `result.md` (tabela por tipo).
