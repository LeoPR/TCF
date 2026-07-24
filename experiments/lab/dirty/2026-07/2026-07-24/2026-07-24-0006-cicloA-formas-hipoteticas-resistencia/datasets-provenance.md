# Proveniência — formas hipotéticas / resistência

**Fonte**: 100% sintético/determinístico, escrito literalmente em `inputs/<ID>-fonte.json`. Nenhum
download, nenhum dado real, sem aleatório. Datasets minúsculos de propósito — o objeto de estudo é a
MOLDURA, e o foco declarado do projeto é payload pequeno.

**Datasets TIPADOS** (o gate exige que o tipo volte):
`D-bool` `[True,False,True,True]` · `D-int` `[1,2,3,42]` · `D-float` `[1.5,2.25,3.0]` ·
`D-str` `["ana","bruno","carla"]` · `D-n1` `[True]` (N=1) · `D-n0` `[]` (N=0).

**Variações de resistência** (63 combos por forma):
- `nome` ∈ {ausente, `doc`, `b` (=tag de tipo), `M` / `H` (=Eixo-1), vazio, `a b`, `9x`, `ção`}
- `id` ∈ {`b`, `n`, `s`, `cpf`, `M` (adversarial), `zz` (desconhecido), vazio}

**REAL × HIPOTÉTICO — a separação que este lab respeita**:
- `outputs/*-wire-real.tcf` e `outputs/*-dataset.roundtrip.json` = o que o `src/tcf` REALMENTE
  produziu (âncora de comparação).
- `intermediates/*-hipotetico-F6.tcfp` = PROTÓTIPO. **O corpo dentro dele é REAL** (vem de
  `encode(valores_renderizados)`); só o header é hipotético. Nenhuma forma inventada vai pra
  `outputs/`.

**Renderização de tipo**: bool → `true`/`false`; int → `str`; float → `repr`. É a convenção do lab
para levar o valor ao corpo textual; o tipo viaja na TAG e é restaurado no decode (é o gate).
`null` NÃO é coberto — fica declarado como lacuna aberta.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. O gate de tipagem (`decode` devolve o
dataset tipado) é condição para qualquer número ser reportado. Zero toque em `src/tcf`.
