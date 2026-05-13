# Análise cruzada — existe formato sempre ótimo?

Comparação dos resultados das 5 condições (unordered + 4 sortings), aplicando
a melhor estratégia C11-híbrida em cada uma.

---

## Tabela mestre

| Condição | Bytes | nome | produto | quantidade | valor |
|---|---|---|---|---|---|
| C1 (CSV) | ~762 | — | — | — | — |
| C2 (col literal) | 704 | 199 | 233 | 72 | 157 |
| Unordered + C11-híbrido | **415** | dict 98 | dict 109 | lit 72 | dict 93 |
| Sort-nome + C11-híbrido | **387** | RLE 70 | dict 109 | lit 72 | dict 93 |
| Sort-produto + C11-híbrido | **379** | dict 98 | RLE 79 | RLE 65 | dict 94 |
| Sort-quantidade + C11-híbrido | **389** | dict 98 | dict 109 | RLE 46 | dict 93 |
| **Sort-valor + C11-híbrido** | **369** | dict 98 | RLE 101 | RLE 62 | RLE 65 |
| Cota teórica (entropy) | ~100 | — | — | — | — |

(Headers ~43B em todos os totais com C11.)

---

## Achados estruturais

### 1. Não há formato sempre ótimo

Cada coluna escolhe estratégia diferente em cada condição. **Em todas as
condições, a estratégia ótima por coluna mudou.** Por exemplo:

| Coluna | Estratégia ótima depende de |
|---|---|
| nome | sort-nome → RLE; outras condições → dict-bare |
| produto | sort-produto/valor → RLE; outras → dict-bare |
| quantidade | sort-(produto/qty/valor) → RLE-local; unordered/sort-nome → literal |
| valor | sort-valor → RLE; outras → dict-bare |

**O encoder ideal escolhe RLE/dict/literal por coluna, dependendo do estado
da ordem.** Isso confirma a hipótese do C11-híbrido como abordagem certa.

### 2. RLE só vence dict quando há runs longos contíguos

Padrão observado: RLE supera dict-bare quando a coluna tem ≥3 runs com
length ≥3, OU quando um run domina (>50% das ocorrências).

| Coluna em qual condição | Tem run dominante? | RLE vence dict? |
|---|---|---|
| nome em sort-nome | sim (4 runs de 4) | sim (70 vs 98) |
| produto em sort-produto | sim (8 runs perfeitos) | sim (79 vs 109) |
| produto em sort-valor | parcial (alguns ×3-6, alguns solo) | sim por pouco (101 vs 109) |
| produto em sort-qty | runs fragmentados (×6+×1, ×2+×3) | NÃO (151 vs 109) |
| valor em sort-valor | sim (vários ×4-6) | sim (65 vs 93) |
| quantidade em sort-X | runs curtos mas distribuídos | RLE > literal mas perde para dict |

Limiar empírico: **RLE precisa que o "topo do histograma" da coluna seja
dominante depois do sort**. Caudas longas e fragmentação favorecem dict.

### 3. Dict implícito é o "default seguro"

Dict-bare nunca foi pior que literal numa coluna não-numérica nesse dataset.
E não depende da ordem. Vira o "fallback" natural quando RLE não resolve.

Quantidade é a exceção: como valores colidem com índices, dict precisa
marcador (`:N`) que custa 1B/ref. Em coluna de cardinalidade média
(12 únicos / 30 linhas) o overhead come o ganho. **Para colunas inteiras
puras, literal continua sendo a escolha quando RLE não rende.**

### 4. O sort ideal arrasta o maior número de "passageiros" junto

Ranking por correlação efetiva no dataset:

- **valor** → produto (forte) + quantidade (parcial) = arrasta 2 passageiros
- **produto** → quantidade (parcial) + valor (parcial) = arrasta 2 fracos
- **quantidade** → produto (parcial) = arrasta 1
- **nome** → ninguém = arrasta 0

Por isso sort-valor venceu — não porque valor tem mais repetição, mas
porque sort-valor produziu o maior NÚMERO de colunas com runs úteis.

### 5. Cota teórica (entropy) está em ~100B; conseguimos 369B

Estamos a ~3.7× do limite teórico de informação. O gap vem de:
- Linha-a-linha (\n por valor) é ineficiente vs bit-packing.
- Strings repetidas no dict (mesmo a primeira aparição é "literal").
- Marcadores (`*`, `:`) custam 1B cada.

**Não há formato textual que chegue perto da cota.** Para chegar lá precisaria
binário (varint, huffman, etc.) — fora do escopo do TCF. O TCF tradeia
compressão por legibilidade humana e por LLM.

---

## Resposta à pergunta da teoria da complexidade

> "Um formato será melhor que o outro SEMPRE, ou existe combinação onde
> um é diferente do outro?"

**Resposta empírica deste dataset:** não existe formato universalmente ótimo
no nível **arquivo inteiro**, mas existe um padrão estável no nível **coluna**:

```
encoder ótimo (por coluna):
  if valores são string e há runs ≥ 3:        → RLE
  elif valores são numéricos e há runs ≥ 3:   → RLE
  elif valores não-numéricos com repetição:   → dict-bare implícito
  elif valores numéricos com repetição alta:  → dict-marcado (`:N`)
  else:                                       → literal
```

Esse algoritmo NÃO É universalmente ótimo — cenários onde quebra:

1. **Cardinalidade extrema (N únicos = N linhas).** Tudo vira literal,
   nenhum schema ajuda. RLE/dict são overhead puro. Literal vence.
2. **Tipo de dado que tem padrão exploitável fora do dict/RLE.** Ex:
   timestamps sequenciais → delta encoding ganha de tudo (não testado).
   IDs com prefixo comum → prefix-stripping ganha. Strings com sufixo
   comum → suffix dict. **Cada padrão de dado pede um esquema próprio**.
3. **Streaming infinito.** Dict implícito carrega memória crescente. Aí
   C12 (com reciclagem) começa a ganhar mesmo perdendo bytecount estático.
4. **Quando o critério não é tamanho, mas latência.** Ex: chunks pequenos
   self-contained pra entrega prioritária — formato fica maior, mas o
   sistema responde mais rápido. Não é o eixo deste arquivo.

### Implicação para o formato TCF

Não existe um único nível L0/L1/L2/L3 que seja sempre o melhor.
**O encoder precisa decidir por coluna**, e o header precisa declarar a
escolha por coluna pra o decoder saber como ler.

Algo tipo:
```
# col nome encoding=dict-bare
# col produto encoding=rle
# col quantidade encoding=rle
# col valor encoding=rle
```

(Ou auto-detectado pelo decoder via heurística — opção em aberto.)

Isso reforça a Decisão 1 do PLANO-formato-adaptativo: **encoding por coluna**,
não por arquivo. O "nível de compressão" do TCF deveria ser visto como uma
**política de seleção** (quais colunas escolhem RLE, dict, literal), não
um modo monolítico.

---

## Hipótese para validar em escala

> Conforme N (linhas) cresce mantendo cardinalidade fixa, dict-bare cresce
> linearmente com N (1 ref por linha repetida) enquanto RLE-pós-sort cresce
> sub-linearmente (1 entrada por run, e runs ficam mais longos).
>
> Logo: para N grande, RLE pós-sort domina dict-bare; para N pequeno, dict
> domina RLE; existe um cruzamento N* dependente da cardinalidade.

Não calculado aqui — fica para experimento de escala depois.

---

## Próximos passos sugeridos

1. **Validar a heurística de seleção por coluna** com um dataset terceiro
   (cardinalidade alta, baixa, mista).
2. **Atacar quantidade** (a chata): testar dict com marcador mais curto, ou
   RLE-pós-sort dedicado, ou delta encoding.
3. **Testar combinação RLE + dict referenciado** (`3:Caneta` + `2*3:`) que
   ficou em aberto na mesa anterior.
4. **Não cair na armadilha de microbytes**: o objetivo da mesa é mapear
   COMPORTAMENTO; bytes são proxy. A análise estrutural (qual estratégia
   vence onde) é mais durável que o número exato.
