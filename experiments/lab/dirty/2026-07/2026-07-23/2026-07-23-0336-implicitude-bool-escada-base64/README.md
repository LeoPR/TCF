# 2026-07-23-0336 — Escada de implicitude do BOOL: base64 vs cru vs 0/1 vs RLE

Responde à pergunta do owner: **"veja se deixar menos binarizado, como uma base64, deixaria o
arquivo melhor"**. Continua a [regra de implicitude](../../../notas/2026-07/2026-07-23-0259-implicitude-singlecol-logica.md)
no caso bool — que é um spec notório de 2 símbolos, onde a tag `b` já fixa o domínio {false,true}
(logo os literais `true`/`false` no body são redundantes) e cabe bit-packing (8 bools/byte).

**Base factual**: ficha de fatos `wf_8ac9d847` (workflow de 5 leitores sobre o core) — wire atual
verificado = **1533 B** (RT OK); `^N` = back-ref de linha ao eid; bit-pack é **100% lab, não-welded**;
`_pack`/`_unpack` reusados da IDEIA de [`2026-07-07-0028-spec-bitwidth-bN/bitpack.py`](../../2026-07-07/2026-07-07-0028-spec-bitwidth-bN/bitpack.py).

## Estado

- **é**: escada MEDIDA (bytes + gzip + RT + equiv-JSON) das 7 formas do bool single-col.
- **será**: SE o modo denso for adotado, entra como candidato `min()` por-coluna (nunca-pior) — não default. Weld só depois de aprovado (owner: "depois de testados a gente pode soldar tudo").

## Resposta curta (ver `result.md`)

1. **base64 vs cru**: base64 paga **+33%** (84 vs 63 B de payload) mas mantém o `.tcf` **textual/válido**;
   **depois do gzip a diferença some** (`alt`: cru=37=b64=37 B). Como arquivo texto, base64 é melhor
   que o cru — o cru (63 B) nem é UTF-8 válido, quebra o invariante inspecionável. `hex` custa +100%.
2. **Não é ganho universal**: bit-pack esmaga bool de ALTA entropia (`rand-50`: 1533→97), mas o `.8H`
   ATUAL já ganha na BAIXA entropia (`all-true`: 36 B < 97). ⇒ candidato de `min()`, não default.
3. **Ganho garantido e ortogonal** = a **implicitude do tipo** (a tag `b` dispensa `true`/`false` no
   body). O modo denso (base64) é um bônus para o regime de alta entropia.

## Como rodar

```
python run.py     # 5 datasets × 7 formas = 35 medições · esperado 0 falhas de equivalência
```

## Formas (todas self-contained, `n` inline, domínio bool IMPLÍCITO, bit1=true)

`json` (N0 ref) · `tcf-atual` (N1, encode REAL) · `p-01` (N2, 1 char/bool) · `p-bin` (N3 cru, ⚠️binário)
· `p-b64` (N3 base64, a pergunta) · `p-hex` (N3 hex) · `p-rle` (N4, depende de runs). Protótipos N2–N4
são **lab-local** — não tocam `src/tcf`.

## Layout

`inputs/<ds>.json` · `outputs/<ds>.<forma>.{tcf,tcfp,bin}` (wire real; `.bin` = binário cru) · `result.md`.
