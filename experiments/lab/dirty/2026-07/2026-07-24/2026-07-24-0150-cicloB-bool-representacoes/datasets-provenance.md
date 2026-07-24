# Proveniência — Ciclo B bool

**Fonte**: 100% sintético/determinístico, escrito literalmente em `inputs/<id>-fonte.json`. Nenhum
dado real, nenhum download. Os perfis aleatórios usam LCG local (seeds fixas por perfil), sem `random`
global. N=64 nos perfis principais (pequeno/inspecionável; o objeto é comportamento, não volume).

**Perfis (plano §S2 perfis mínimos)**: `n0` (`[]`) · `n1` (`[True]`) · `all-true` · `all-false` · `alt`
(alternado) · `runs` (blocos) · `p10`/`p50`/`p90` (proporções de true, seed fixa). Cobrem constante,
alternância, runs e as proporções que separam RLE-favorável de denso-favorável.

**Homógrafos**: `[True,False]` (bool) · `["true","false"]` (string) · `[1,0]` (number) — mesma grafia,
tipos distintos; testa que o tipo volta pelo dataset.

**Real × hipotético**: `outputs/*-wire.tcf` = o que `encode` do `src/tcf` REALMENTE emite (âncora). As
representações `typed`/`bN`/`misto` são PROTÓTIPOS lab-local (kit `pecas.py` do lab 1759 p/ pack_w/
seg_adapt) e vivem em `intermediates/*.tcfp`, marcadas — o header `#TCF.8b` e os modos `~d`/`~x` são
HIPÓTESE (#4 não soldado).

**Gate**: RT-TIPADO — cada representação decodifica de volta a `list[bool]` e é comparada ao dataset
original (bool == bool, não string). Bytes/gzip só reportados com RT ✅. gzip é lente (filosofia do
projeto), não critério.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. Zero toque em `src/tcf`.
