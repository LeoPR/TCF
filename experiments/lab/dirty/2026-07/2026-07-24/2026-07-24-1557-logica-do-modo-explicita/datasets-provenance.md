# Proveniência — lógica do modo explícita

**Fonte**: 100% sintético/determinístico, `inputs/*-fonte.json`. Nenhum dado real, sem `random` global
(perfis aleatórios via LCG local, seeds fixas). Bool, N=64 (+ n1). O objeto é a LÓGICA (variável de
modo), não volume nem compressão de produto.

**Perfis**: all-true/all-false (core/RLE vence) · alt/p50/p90 (denso vence) · runs/p10 (denso) · n1.
Cobrem os dois ramos da variável `modo` (core e denso).

**Protótipo lab-local**: reusa o core REAL do `src/tcf` (`encode`/`decode` para o corpo core, mode A) e
o `pack_w`/`unpack_w` do kit `pecas.py` (lab 1759) para o denso bN. O header `#TCF.8b`, o char de modo
`1/2/4/8` e a variável `modo` são a gramática HIPOTÉTICA do #4 (não soldado) — vivem só neste lab.

**Gate**: RT-TIPADO — decode devolve `list[bool]` == original (bool volta bool). Bytes só com RT ✅. Um
bug de domínio-por-ordem-de-aparição foi pego pelo gate e corrigido (bool = convenção fixa false=0/
true=1); documentado no README.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. Zero toque em `src/tcf` — é a referência
explícita pronta pra promover ao weld.
