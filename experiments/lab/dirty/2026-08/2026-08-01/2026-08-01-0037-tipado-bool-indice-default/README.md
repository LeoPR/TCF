# 2026-08-01-0037 — T-TIPADO-BOOL-INDICE: slots congelados DEFAULT da tag `b`

O denso b2 (ADR-0037, weld 2026-07-31) fechou o ternário **denso**, mas o candidato
**CORE/RLE** seguia emitindo `true`/`false` como NOMES — o null já viajava como `0` cru
(slot 0 pré-alocado), só os valores pagavam nome. Proposta aprovada pelo owner: o render da
tag `b` vira **slots congelados**, o MESMO domínio do b2 — `null=0` (já era), `false=1`,
`true=2` — emitidos como `\1`/`\2` pelo `_escape_lit` de sempre. Decode: slots canônicos
(único emitido); nomes decodáveis-não-emitidos (contrato do modo `C`, ADR-0036).

## O ganho (hoje = nomes × slot)

| coluna | n | modo | hoje | slot | Δ |
|---|---:|:-:|---:|---:|---:|
| `bool-constante` (`[True]*200`) | 200 | core | 18 (`*200\|true`) | **16** (`*200\|\2`) | −2 |
| `run-heavy-1` | 200 | core | 30 | **25** | −5 |
| `runs-4` | 200 | core | 41 | **34** | −7 |
| `runs-10` · `alternado` | 200 | b1 | 47 | 47 | 0 |
| `alternado-null` | 200 | b2 | 79 | 79 | 0 |
| `real-adult-sex-ordenado` | 100 | core | 27 | **22** | −5 |
| `real-adult-sex-ord-null` | 100 | b2 | 47 | 47 | 0 |
| `real-adult-class-ordenado` | 100 | core | 27 | **22** | −5 |

Δ somado: **−24 B**; slot menor em 5 de 11, **nunca pior em nenhuma**.

## O caso run-heavy — confirmado

`[True]*100 + [None] + [False]*99`: o **CORE vence o b2 nos dois renders** (30/25 B vs 79 B
do b2) — é exatamente o caso que escapava do weld b2, e é onde o slot economiza (−5 B). Nos
modos densos o render não muda nada (Δ = 0, modo idêntico): o corpo core nem materializa.

## Veredito das 4 adversidades

1. **Polaridade sobre slots: inerte por construção.** Corpo bool em slots tem **no máximo 2
   linhas literais** (`\1`, `\2`); transições literal↔referência ≤ 4, o sufixo nunca
   compensa. Varredura direta de `polariza` nos 11 corpos: **0 disparos**.
2. **seq-RLE sobre `1,2,1,2…`: não dispara** — delta não-uniforme (1↔2); e o alternado vai
   pro denso (b1/b2) nos dois renders, sem corpo.
3. **Legado: OK** — `#TCF.8b\ntrue\nfalse\n^1\n` decodifica `[True, False, True]` pelo cast
   novo (nomes = decodável-não-emitido, contrato do modo `C`).
4. **Fail-loud: 3/3** — `\0`, `\3`, `\15` no corpo tipado-b → `ValueError`
   (`outputs/fail-loud.txt`).

## Validação

RT estrito (valor, tipo, comprimento) + **roundtrip ARQUIVO** byte-idêntico em todas as
colunas (assert no `run.py`). O protótipo (`slot_render.py`) usa `_encode_column`,
`polariza`, `despolariza`, `_decode_column`, `pack_w` do `src/tcf` — só o render e o cast
são novos. **`src/tcf` intocado.**

## Limites

- Nada soldado; os `-slot.tcf` são proposta — o decode público ainda não conhece `1`/`2` no
  corpo tipado.
- Ganhos pequenos em bytes absolutos por coluna (−2 a −7 B), mas no regime onde o core/RLE é
  o vencedor — complementar ao b2, não concorrente.
- gzip e CPU não medidos.

## Rodar

```
python run.py
```

Sai `0` só se RT passar em todas as colunas, o run-heavy confirmar o core vencendo o b2 nos
dois renders, e as 4 adversidades verificarem.
