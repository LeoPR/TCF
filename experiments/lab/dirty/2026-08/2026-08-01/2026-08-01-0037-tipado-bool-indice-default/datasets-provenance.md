# Proveniência — T-TIPADO-BOOL-INDICE, slots DEFAULT da tag `b` (2026-08-01-0037)

## Por que este lab existe

O weld do denso b2 (ADR-0037, 2026-07-31) fechou o ternário DENSO. O caso que escapava: o
candidato CORE/RLE da rota tipada bool, onde `true`/`false` viajam como NOMES. O owner
aprovou slots congelados (`null=0` já existente, `false=1`, `true=2`) como grafia DEFAULT.
Este lab mede o ganho e as adversidades antes do weld.

## Sintéticas — determinísticas, sem RNG

Construídas por repetição/fatias sobre o índice. **Sem `random`, sem relógio, sem rede.**

| coluna | construção | o que exerce |
|---|---|---|
| `bool-constante` | `[True]*200` | o caso-motivação: `*200\|true` (18 B) → `*200\|\2` (16 B) |
| `run-heavy-1` | `[True]*100+[None]+[False]*99` | onde o CORE vence o b2 (ternário de runs) |
| `runs-4` · `runs-10` | 4/10 runs alternados, n=200 | segmentação crescente — onde o denso retoma |
| `alternado` | `[True,False]*100` | controle FLOOR: sem null → b1 nos dois renders |
| `alternado-null` | null a cada 3º | controle FLOOR: com null → b2 nos dois renders |
| `tiny-constante` · `tiny-ternario` | n=3 | tiny-n; o empate core×denso (14=14) |

## Reais — fixtures já commitadas

**Nenhum download.** `datasets/samples/adult-census/adult-sample.csv` (o mesmo fixture dos
labs `2026-07-28-0829` e `2026-07-31-2350`). O CSV dá STRING; o lab converte para `bool` —
conversão idêntica aos labs anteriores — e **ordena por grupo** (`sorted`) para formar o
run-heavy realista. Nulls, quando presentes, injetados pelo lab a cada 7º elemento. Escolha
DO LAB, não do dado.

| coluna | campo | conversão | null |
|---|---|---|---|
| `real-adult-sex-ordenado` | `sex` | `v.strip() == "Male"`, sorted | — |
| `real-adult-sex-ord-null` | `sex` | idem | a cada 7º (`i%7==0`) |
| `real-adult-class-ordenado` | `class` | `">" in v`, sorted | — |

## Validação — e por que não é circular

```
dados -> _tipo_single_col (src/tcf) -> tag 'b'
      -> render SLOT (a única peça nova do encode): None/"1"/"2"
      -> _encode_column(header="val") + polariza + pack_w b1/b2  (tudo src/tcf)
      -> min() dos candidatos (mesma regra do encoder real)
      -> proto_decode: despolariza + _decode_column (src/tcf) + cast_slots (peça nova)
         | modo denso b1/b2 -> decode() público, já soldado
      -> compara com os DADOS ORIGINAIS (valor, tipo, comprimento)
```

O mecanismo de corpo (core, polaridade, seq-RLE, RLE, bitpack) é 100% `src/tcf` — as únicas
peças medidas são o render e o cast, que é o que a solda trocaria. Roundtrip é ARQUIVO:
`outputs/<nome>-dataset.roundtrip.json` byte-idêntico a
`intermediates/<nome>-dataset-consumido.json`, com assert no `run.py`.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `-slot.tcf` são proposta — o decode público
  ainda não conhece os slots `1`/`2` no corpo tipado.
- Ganhos pequenos por coluna (−2 a −7 B), no regime core/RLE — complementar ao b2.
- As colunas reais são **convertidas e ordenadas pelo lab**; nulls **injetados pelo lab**.
- **gzip e CPU não medidos.**
- Fail-loud medido no cast (`\0`, `\3`, `\15`); evidência em `outputs/fail-loud.txt`.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relógio, sem rede. Sai `0` só se RT
passar em todas as colunas, o run-heavy confirmar o core vencendo o b2 nos dois renders, e
as 4 adversidades verificarem (polaridade inerte, seq-RLE ausente, legado OK, fail-loud 3/3).
