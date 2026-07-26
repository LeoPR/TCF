# 2026-07-25-2107 — O seq-RLE aplica SEM FLOOR

Achado do owner olhando [`C-ruido-n100-wire.tcf`](../2026-07-25-2036-inteiros-variacoes-ordem-null/outputs/C-ruido-n100-wire.tcf):
o encoder emite marcadores de delta em dado **aleatório**, e o marcador custa mais do que
economiza.

```
*2+498217|\168116      17 B   ← marcador com delta
\168116⏎\666333⏎       16 B   ← os dois literais crus
```

**Confirmado no código.** `hcc_seqrle.encode` termina com:

```python
compacted, info = compact_body(body_lines)
return "\n".join(compacted) + "\n"        # sem comparar com body_text
```

Aplica **incondicionalmente**. O custo do marcador nunca entra na decisão — que é
exatamente o que o owner suspeitou.

## Resultado — 16 casos, RT 32/32

| forma | o que é |
|---|---|
| `bruto` | corpo com `hcc_seq_rle=False` (o que o `super().encode` produz) |
| `sempre` | comportamento **atual** |
| `floor` | `min(bruto, sempre)` — o que a correção emitiria |

**O seq-RLE piorava em 7 de 16 casos.** Economia do FLOOR nesta matriz: **929 B**. E em
nenhum caso ele piora — é `min`, nunca-pior por construção.

### Onde perdia

| id | bruto | sempre | perda |
|---|---:|---:|---:|
| `A-ruido1000000-n1000` | 7854 | 8573 | **719 B** |
| `A-ruido1000000-n100` | 793 | 867 | 74 B |
| `A-ruido100-n1000` | 3899 | 3948 | 49 B |
| `A-ruido100-n100` | 383 | 422 | 39 B |
| `C-seq-com-ruido` | 1121 | 1157 | 36 B |
| `A-ruido10-n100/1000` | 310/3104 | 316/3110 | 6 B |

~8–9% do corpo em ruído de alta cardinalidade.

### Onde ganha (e o FLOOR preserva)

`B-seq-n1000` 4890 → **31** · `B-ids-n200` 1600 → **15** · `B-passo5-n200` 978 → **30** ·
datas ISO e emails também ganham. **O FLOOR não toca em nenhum desses.**

### A fronteira

`C-blocos` (100 sequenciais + 100 aleatórios): o seq-RLE ganha no total (853 vs 1179) mesmo
com metade de ruído — os marcadores bons compensam os ruins. É o caso que justifica o FLOOR
ser **por corpo** e não "desligar em dado desordenado".

## Por que por-corpo e não por-marcador

Testei as duas granularidades. O FLOOR **por marcador** (manter só o marcador que paga)
deu **exatamente o mesmo resultado** em todos os casos, inclusive no misto — dentro de um
corpo os marcadores são uniformemente bons ou uniformemente ruins. A versão simples basta;
a fina só adicionaria complexidade.

## Impacto medido da correção (experimento aplicado e revertido)

| | |
|---|---|
| gates byte-canônicos | **passam sem mudança** — D1-D9, D17a e real-world nunca eram prejudicados |
| pinos hierárquicos | **7 encolhem** (ex.: 3134 → 3132; um size de header 8 → 6) |
| resto da suíte | intacto |

Ou seja: a correção é melhora pura, e o re-pin é de valores que **diminuem**.

## Rodar

```
python run.py     # 16 casos; regenera evidências + result.md
```

`outputs/<ID>-wire.tcf` (REAL, comportamento atual) · `<ID>-sem-seqrle.tcfp` (a variante
sem marcador — **também é um wire válido**, o decode só expande o que existe) ·
`<ID>-equivalente.json` · `<ID>-dataset.roundtrip.json`.

**Este lab não toca `src/tcf`.**
