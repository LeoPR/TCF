# Resultado — binarizar pelo espaço do tipo funciona, e o nicho é preciso

6 casos × 5 formas + o ponto de virada em 11 cardinalidades. **0 falhas** de RT.

## A resposta curta

**Sim, faz sentido — e o nicho começa exatamente onde o `bN` acaba.** Mas com três ressalvas
que a medição impõe, e uma delas inverte a intuição.

## As formas medidas

| caso | k | n | texto | ord-decimal | tipo-17b | tipo-5+6+6 | vencedor |
|---|---:|---:|---:|---:|---:|---:|---|
| batimento 15 min, 7 dias | 96 | 672 | 1541 | **1434** | 1919 | 1918 | ord-decimal |
| batimento 15 min, 1 dia | 96 | 96 | 751 | **42** | 286 | 285 | ord-decimal |
| cada minuto | 1440 | 1440 | 465 | **53** | 4095 | 4094 | ord-decimal |
| cada segundo | 2000 | 2000 | 671 | **50** | 5683 | 5682 | ord-decimal |
| só hora cheia | 24 | 2000 | **1705** | 1837 | 5683 | 5682 | texto (bN) |
| **`retail` real** | **564** | 2000 | 10619 | 10120 | 5683 | **5682** | **tipo (−46,5%)** |

## 1. Por campo e por ordinal custam o mesmo — e não é coincidência

`5 + 6 + 6 = 17` bits, e `ceil(log2 86400) = 17` também. Porque `2^5 · 2^6 · 2^6 = 131072 = 2^17`.
Medido: **5682 contra 5683 B** — 1 byte de diferença, que é ruído de arredondamento do base64.

**Então a escolha entre campo e ordinal não é de tamanho — é de que estrutura sobra.** E a
medição mostra que, uma vez empacotado, **não sobra nenhuma**: as duas formas são planas.

## 2. A inversão: binarizar DESTRÓI a estrutura que o núcleo explora

Nos regimes regulares o **ordinal decimal** vence por ordens de grandeza:

- cada minuto: **53 B** contra 4095 do bit-packed — **77×**
- cada segundo: **50 B** contra 5683 — **114×**

Porque o ordinal decimal é uma **progressão aritmética** e o seq-RLE a esmaga para ~50 bytes
*independentemente de n*. O bit-packing tem piso `n × 17/8 × 4/3 = n × 2,83` bytes, e **nada o
faz descer** — depois do base64 não há mais aritmética visível.

É a mesma lição do `data-iso`, que escolheu decimal em vez de denso justamente para *"deixar a
aritmética visível"*.

## 3. O ponto de virada é o `MAX_W = 8` do `bN` — um limite de NAMESPACE

Com `n=2000` e ordem irregular (cardinalidade isolada da regularidade):

| k | núcleo | tipo-17b | vence | header do núcleo |
|---:|---:|---:|---|---|
| 96 | 3136 | 5683 | núcleo | `#TCF.8B77d0` |
| 144 | 3921 | 5683 | núcleo | `#TCF.8B87d0` |
| **288** | 9838 | **5683** | **tipo** | `#TCF.8` ← **o bN sumiu** |
| 1279 | 15768 | **5683** | **tipo** | `#TCF.8!!` |

**A virada é exatamente onde o núcleo para de usar o `bN`** — o header vai de `B87d0` (w=8)
para literal puro. E o motivo está no código: `dominio_bn.py:70` — `MAX_W = 8`, *"teto do
namespace: `w` de 1 a 8 → até 256 valores distintos"*, porque a largura ocupa **um dígito só**
no header (`campos[0] not in "12345678"`).

**Não é uma escolha de compressão — é o tamanho do campo no cabeçalho.** Acima de 256
distintos o `bN` não qualifica e não há candidato denso nenhum. **É exatamente aí que a
binarização pelo espaço do tipo existiria**, e é por isso que ela ganha 46,5% na coluna real
(564 distintos).

A álgebra confirma a medição: o denso vence enquanto `n < 6·[k·(L+1) + 2] / (17 − w)`, com
`L=11` (a grafia **escapada** `\08:\30:\00`). Para `k=256, w=8` isso dá `n < 2049` — e a
medição a `n=2000` bate.

## 4. Três coisas que a álgebra expõe e a medição não mostra sozinha

- **`w` é escolha de resolução, não constante.** `HH:MM` são 1440 valores → `w=11`;
  `HH:MM:SS` → 17; com milissegundos → 27. **Cada bit a mais custa `n/6` bytes**, e cada
  segundo de resolução descartado devolve `n/6`.
- **O null sai de graça.** `2^17 = 131072 > 86400` deixa **44.672 códigos livres** — null e
  reservados cabem no desperdício de arredondamento, custo **zero**, como o slot `3` do `b2`.
  No `bN` o null é mais um valor do domínio e pode empurrar `w`.
- **O denso não tem o teto de 256** — ele é o único candidato possível na faixa de 257 a 86400.

## 5. Prior art: o princípio existe, a aplicação a uma FAIXA não

- **ADR-0037** é o precedente exato do princípio, e o título é literalmente *"domínio
  IMPLÍCITO"*: *"a pergunta não é 'como declarar o domínio', é **'quando o domínio pode NÃO
  viajar'** — quando ele é fixo por tipo"*. Medido lá: os **15 B** entre `b2` (79) e o bN
  tipado (94) *"são exatamente o domínio declarado que deixou de viajar"*.
- **`H-DENSE-MODE-01`** (owner, 2026-07-23) chega perto: fala em *"marcador que declara tipo,
  bit-width e alfabeto"* e em *"campo binário arbitrário"* — mas ali isso significa **bytes
  opacos**, e a largura é sempre *do elemento*, nunca de uma **faixa**.
- **`w` derivado de faixa: NÃO EXISTE** no repo. Todas as 9 ocorrências de `log2` são
  `ceil(log2 k)` com k = distintos observados.
- E a hora é **o exemplo canônico do ponto cego**, registrado desde 2026-05-27 em ADR-0018:
  *"beijing `hour`, 24 únicos → **228,8%** de inflação… entropia ~5 bits/linha, poderia ir de
  228,8% para <15%"* — **nunca perseguido por esta via**.

## 6. Os bloqueios reais

1. **`w=17` não cabe na gramática de hoje.** O `<modo>` do índice 7 é **mono-char**
   (`decoder.py:429`, `resto[:1]`), então `"17"` seria lido como modo `1` e `n=0x7`. Esta é a
   **única mudança de wire** que a ideia exige — e já está prevista: o namespace de modo reserva
   letras para *"subtipos mapeados"*, com estado *"PREPARADO, não construído"*.
2. **`pack_w` não valida faixa.** `format(3, "01b")` devolve `"11"` sem truncar, então
   `pack_w([3,0], 1)` corrompe em silêncio. Hoje é inalcançável (todos os chamadores constroem
   os índices), mas um modo por espaço do tipo põe a checagem `0 ≤ v < 86400` **na conta do
   chamador**.
3. **`24:00:00` está fora de `0..86399`** — é a peculiaridade (4) do fechamento da hora
   cobrando: grafia ISO legal que uma largura derivada do tipo não representa.
4. **O ganho é terminal, não de transporte.** A escada base64 de 2026-07-23 mediu que
   cru e base64 **empatam depois do gzip** (37 e 37 B), e o gate real-world do bN deu **8,8%
   terminal contra 1,7% pós-brotli**.

## O que isto orienta

**A ideia tem nicho, e o nicho é definido por um limite de namespace, não por natureza do
dado.** Registrar como hipótese própria — `H-DENSE-MODE-03`, irmã das duas do owner — enunciada
como *"largura do espaço do TIPO em vez da cardinalidade do domínio; o domínio não viaja"*,
com três condições de aplicabilidade medidas:

- **k > 256** (acima do `MAX_W` do bN), **e**
- ordem **irregular** (sem progressão que o seq-RLE explore), **e**
- ganho lido como **terminal**, não pós-compressor.

A coluna real do corpus satisfaz as três — e é onde ela dá 46,5%.
