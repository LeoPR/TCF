# ADR-0036 — bN de domínio: densidade por CARDINALIDADE

- **Status**: aceito (weld 2026-07-27)
- **Escopo**: single-col flat (`_lista_flat`). **Fora**: rota tipada, `.8M`, `.8H`, spec, órfão.
- **Interage com**: ADR-0024 (baselines re-pináveis), ADR-0032 (discriminador),
  ADR-0035 (polaridade — o candidato irmão no mesmo `min()`).

## Contexto

Uma coluna de 200 valores `"0"`/`"1"` custava **609 B** — 2 literais e 198 referências de
linha (`^N`), ~3 B por linha. A mesma informação como `bool` nativo custava **47 B** (modo
denso `b1` + base64).

A diferença não é de conteúdo, é de **rota**: `list[str]` cai no `_lista_flat` e nunca chega
ao `_tipo_single_col`, onde o denso mora. E o denso é bool-**sem-null** por construção, então
`bool + null` também caía no core (546 B).

**A oportunidade é da cardinalidade da coluna, não do tipo Python da entrada.**

## Decisão

Com `k` valores distintos, bastam `w = ceil(log2(k))` bits por linha. O domínio viaja uma
vez; os índices viajam empacotados em base64.

```
#TCF.8                    #TCF.8B178
\0                        false
\1                        true
^1                        =CIhmASAEyQvAQQZokA
^2   …  (609 B)                 (57 B)
```

### Duas grafias, escolhidas pelo TRANSPORTE — não pelo tamanho

| | | |
|---|---|---|
| **`B`** | domínio **primeiro**, `=` abre os bits | **default** — streama nos dois lados |
| **`C`** | domínio por **último**, sem marcador | lote fechado — ~1 B menor |

O `C` é ~1 B mais barato e **venceria sempre num `min()` cego**. Mas ele **não streama**: o
leitor precisa do payload inteiro antes de emitir o primeiro valor — numa coluna de 2000
linhas, **1764 B de buffer contra 100 B**, 17× (lab `2211`). Trocar streaming por 1 byte, em
silêncio, seria a decisão certa tomada pelo critério errado.

Por isso **só o `B` é emitido por default**; o `C` fica **decodável** (wire de outra ponta lê
normalmente) e o opt-in de emissão é `T-BN-LOTE`.

### O marcador `=` e o escape

O `=` abre o bloco de bits; uma linha de **domínio** que comece com `=` ganha `\` na frente.
Isso é inequívoco porque **o core nunca emite `\` seguido de char fora de `* 0-9 \ ^ ~`** —
medido varrendo os 95 imprimíveis (lab `2231`).

Custo: **1 B** + 1 B por valor de domínio que comece com `=`. Em **145 colunas categóricas
reais** das fixtures, o segundo termo foi **zero**. O caso patológico é absorvido pelo FLOOR
externo: se o bN inchar, o core vence.

Alternativa considerada e descartada: marcador `\|` (imune por construção, 2 B fixos).
Break-even em 1 colisão; declarar qual dos dois foi usado custaria ≥1 B e comeria o ganho
(lab `2247`).

### `null` não é caso especial

É mais um valor do domínio, e ocupa o **slot 0** que o formato já reserva. A grafia do domínio
é a do core: `0` cru = null, `\0` = o literal `"0"`.

Essa assimetria — grafar mais do que se desfaz — já causou **4 bugs** no projeto (weld do slot
nulo, labs `2126`, `1608`, `2231`). `_le_grafia` desfaz exatamente `_grafa`, nem mais, e há
teste travando isso.

### Onde não se aplica

| | |
|---|---|
| `k ≤ 1` | o core já é ótimo com RLE (`*N\|valor` = 16 B); o bN nem se qualifica |
| `k > 256` | `w` passaria de 8 — fora do namespace |
| `n` pequeno | cabeçalho + domínio não se pagam; o FLOOR recusa sozinho |
| valor longo | o teto real é `k × len(valor)`, não `k` |

## Consequências

### Nenhum baseline moveu

D1-D9 **1545**, D17a **300**, real-world **89430** — inalterados. Nenhuma coluna dos gates tem
cardinalidade baixa o bastante para o bN vencer, o que confirma o FLOOR nunca-pior.

Suíte: **1042 passed, 3 skipped** (era 1010). Novo `tests/test_dominio_bn.py` (32).

### Reuso — quase nada é código novo

| peça | de onde |
|---|---|
| `pack_w` / `unpack_w` | `tcf/bitpack.py` — inclusive o fail-loud de payload curto e padding não-zero |
| domínio comprimido | `_encode_column` / `_decode_column` — o domínio é uma mini-coluna |
| garantia do marcador | a gramática de escape do core (`_escape_lit`) |
| ponto de inserção | o `min(candidatos)` que a polaridade já usa |

O `bitpack.py` já dizia no docstring: *"Larguras 1/2/4/8 (o namespace do `<modo>`); só w=1
(bool) é exercido agora"*. Este weld exerce de 1 a 8.

## Aberto — registrado, não esquecido

| ticket | o quê | por quê importa |
|---|---|---|
| **`T-BN-TIPADO`** | levar o bN à rota tipada (`#TCF.8bB…`) | `bool + null` custa **546 B** hoje contra **92 B** possíveis. Não entrou porque o wire `B` devolve **string**, e a rota tipada tem de preservar o tipo — um `bool` voltando `"true"` seria corrupção silenciosa. Exige tag dentro do cabeçalho, que é grafia nova. |
| **`T-BN-LOTE`** | opt-in para emitir o modo `C` | ~1 B/coluna, para quem não lê incrementalmente |
| **`T-BN-MULTICOL`** | o bN no `.8M` | é a decisão pendente que já está no `STATUS.md`; escopo diferente deste |
| **`T-BN-LARGURA-VARIAVEL`** | não desperdiçar slots em `k` = 3, 5, 6, 7 | largura fixa arredonda para cima; `k` potência de 2 é o caso justo |
| **`T-BN-GZIP`** | medir sob gzip | o estudo multi-col registrou que o gzip encolhe muito o ganho do bN |

## Evidência

`experiments/lab/dirty/2026-07/2026-07-27/`: `1608` (a escada `k → largura`), `1647` (domínio
comprimido pelo core + alinhamento exaustivo 936/936), `2211` (o eixo de streaming), `2231`
(marcador por escape), `2247` (o espaço completo de delimitação, 7 opções).
