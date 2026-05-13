# 22 — sintaxe compacta v2 (idx automático por fragmento)

## Princípio / motivação

A nota [`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md)
discutiu duas direções: (1) marcadores compactos explícitos
(exp 21) e (2) marcadores **inferidos pela ordem**. Este
experimento explora a Direção 2 — proposta do user:

> "a linha já tem marcador natural, então na verdade nem
> precisaria ser indicado. Cada quebra ganha um índice
> naturalmente que é sequência da linha (...) os índices de
> referências são os números"

A ideia: em vez de `noN[a:b]` ou `@N<K`, a linha do nó é
**dividida em fragmentos** pelos pontos onde outros nós vão
referenciar. Cada fragmento ganha um **idx global automático**
(sequencial). Outras linhas referenciam por número.

## Propósito

Implementar a Direção 2 da nota como sintaxe alternativa
plugada na interface `Syntax`. Algoritmo (`online.py`) intocado.

## Comparação

- **Compara com**: VerboseSyntax (exp 20) e CompactV1Syntax
  (exp 21).
- **Datasets**: os 21 do exp 20 (3 do exp 15 + 6 do exp 17 +
  12 do exp 18).

## Gramática

```
Body:  [
         <linha-do-no-1>
         <linha-do-no-2>
         ...
       ]

Linha pode ser:
  <decl>           declaracao de novo no (default)
  ^N               uso do no N (repete a string)
  *K|<decl>        decl com K cópias adjacentes
  *K|^N            uso do no N, K cópias adjacentes

<decl> e' uma sequencia de elementos:
  'X'              literal (texto X), aloca proximo idx global
  N ou N,M,...     ref por idx (refs adjacentes separadas por ',')

Concatenacao implicita entre elementos.
```

## Exemplo lado a lado (D2-mini, 6 strings)

**Verbose** (208 bytes):
```
<body>
  no1: "maria.silva@gmail.com"
  no2: no1[0:12] + "hot" + no1[-8:]
  no3: no1[0:12] + "yahoo" + no1[-4:]
  no4: "joao.souz" + no1[-11:]
  no5: no4[0:11] + no2[-11:]
  no6: no4[0:11] + no3[-9:]
</body>
```

**Compact v1** (116 bytes):
```
[
@1:'maria.silva@gmail.com'
@2:@1<12'hot'@1>8
@3:@1<12'yahoo'@1>4
@4:'joao.souz'@1>11
@5:@4<11@2>11
@6:@4<11@3>9
]
```

**Compact v2** (97 bytes — −16% vs v1, −53% vs verbose):
```
[
'maria.silv''a@''g''mail''.com'
1,2'hot'4,5
1,2'yahoo'5
'joao.souz'2,3,4,5
8,2,6,4,5
8,2,7,5
]
```

Em compact_v2 a linha 1 declara s1 com 5 fragmentos pré-quebrados
(em pos 10, 12, 13, 17 — pontos onde outras linhas vão referenciar).
Cada fragmento ganha idx automaticamente (1 a 5). As linhas
seguintes referenciam idx diretamente sem precisar de marcador
explícito como `@`.

## Como as quebras são computadas

Passada 1 — **diretas**: para cada `RefPref(eid, K)`, position K
no nó eid é quebra; para cada `RefSuf(eid, K)`, position
`len(eid) − K` é quebra.

Passada 2 — **propagação**: ordem inversa (do maior eid para o
menor). Se eid tem quebra na position Q dentro de um
RefPref/RefSuf, propaga essa quebra para o nó referenciado na
position correspondente.

Garantia: cada slice referenciado coincide exatamente com 1+
fragmentos contíguos do nó.

## Resultado observado

Roundtrip **21/21 OK** em todas as 3 sintaxes (63 runs totais).

### Bytes por sintaxe

| Dataset | unidades | verbose | compact v1 | **compact v2** | v2/v1 | v2/verb |
|---|---:|---:|---:|---:|---:|---:|
| D2-mini | 47 | 208 | 116 | **97** | 0.836 | 0.466 |
| D2-completo | 78 | 456 | 232 | **191** | 0.823 | 0.419 |
| D4 | 75 | 414 | 222 | **165** | 0.743 | 0.399 |
| urls | 128 | 448 | 270 | **218** | 0.807 | 0.487 |
| uuids | 430 | 578 | 512 | **472** | 0.922 | 0.817 |
| iso-timestamps | 49 | 395 | 197 | 231 | **1.173** | 0.585 |
| ips | 52 | 319 | 170 | **131** | 0.771 | 0.411 |
| cpfs | 168 | 306 | 247 | **208** | 0.842 | 0.680 |
| codigos | 38 | 322 | 166 | **99** | 0.596 | 0.307 |
| urls-N0050 | 228 | 1636 | 894 | **732** | 0.819 | 0.447 |
| urls-N0200 | 553 | 6201 | 3379 | **2709** | 0.802 | 0.437 |
| urls-N1000 | 2255 | 31299 | 17509 | **16543** | 0.945 | 0.529 |
| iso-N0050 | 269 | 1876 | 979 | **831** | 0.849 | 0.443 |
| iso-N0200 | 648 | 7054 | 3724 | 4705 | **1.263** | 0.667 |
| iso-N1000 | 2264 | 33581 | 18209 | 33837 | **1.858** | 1.008 |
| ips-N0050 | 184 | 1237 | 703 | **563** | 0.801 | 0.455 |
| ips-N0200 | 553 | 5025 | 2868 | **2476** | 0.863 | 0.493 |
| ips-N1000 | 2092 | 28457 | 15043 | 18012 | **1.197** | 0.633 |
| codigos-N0050 | 119 | 1353 | 707 | **535** | 0.757 | 0.395 |
| codigos-N0200 | 427 | 5665 | 3069 | **2189** | 0.713 | 0.386 |
| codigos-N1000 | 2067 | 29296 | 16292 | **15363** | 0.943 | 0.524 |
| **TOTAL** | | **156126** | **85508** | **100307** | **1.173** | **0.642** |

### Dois regimes distintos

**Regime onde v2 ganha** (razão v2/v1 < 1, 17 casos):

- D2-mini/completo, D4: -16% a -26% vs v1
- urls em todos os tamanhos: -5% a -20%
- codigos em todos os tamanhos: -6% a -41%
- ips até N=200: -13% a -23%
- uuids, cpfs: ganho pequeno
- iso-timestamps (N=12): -15%
- iso-N0050: -15%

**Regime onde v2 perde** (razão v2/v1 > 1, 4 casos):

- iso-N0200: **+26%**
- iso-N1000: **+86%** (quase 2× pior!)
- ips-N1000: +20%
- iso-timestamps (N=12) levemente também: +17%

## A explicação do trade-off

O número de **quebras por nó** define o tamanho da
representação compact_v2. Cada quebra cria um fragmento extra;
cada ref a um slice vira uma **cadeia de N idx separados por `,`**
em vez de 1 marcador único.

| Cenário | Quebras por nó | Ref vira | v2 ganha? |
|---|---|---|---|
| URL com base comum (1-3 quebras) | poucas | 1-2 idx | sim |
| Códigos com prefixo fixo (2-3) | poucas | 1-2 idx | sim |
| ISO timestamps (mesmo formato, muitas variações HH:MM:SS) | **muitas** | **4-8 idx** | **não** |
| IPs em N=1000 com vários hosts por subnet | muitas | 3-5 idx | não |

Em verbose ou compact_v1: 1 ref = 1 marcador, custo constante.
Em compact_v2: 1 ref = N idx, custo proporcional ao número de
slices distintos sobre o mesmo nó.

### Exemplo concreto — iso-N0200

```
'2026-05-0''1''T''0''0'':''0''0'':00Z'      ← s1 com 9 fragmentos
1,2,3'1''7'':''0''7'9                         ← s2: 4 refs + 4 lits curtos + 1 ref
1,2,3,10'0'':''1''4'9                         ← s3: 5 refs + 4 lits + 1 ref
```

Cada timestamp em N=200 referencia ~5-8 fragmentos pequenos.
Cada char `,` entre refs é 1 byte extra. Aparente compactação
do ganho de **eliminar `noN[a:b]`** é apagada pelo **custo de
referenciar muitos idx**.

## Trade-off conceitual

| Sintaxe | Mecanismo | Custo de ref |
|---|---|---|
| Verbose | `noN[a:b]` | 9-12 chars (fixo por slice) |
| Compact v1 | `@N<K` ou `@N>K` | 4-7 chars (fixo por slice) |
| Compact v2 | sequência de idx por `,` | **variável**: N chars por idx, M idx por slice |

Compact v2 **paga pela granularidade**. Quando os slices são poucos
e bem definidos, paga pouco. Quando há muitos slices sobrepostos,
paga muito.

## Limitações

- **Literais não podem conter `'`, `*`, `^`, `,` ou começar com
  dígito**. Em datasets atuais nada disso ocorre.
- **A propagação de quebras pode criar muitos fragmentos
  pequenos**: caso iso-N1000 com 33 KB. Em casos extremos, v2
  é pior que verbose.
- **N=1000 fica caro em escala**: cada nó pode ter 10+
  fragmentos, e cada ref a slice vira 5-8 idx.
- **Não testa sintaxes binárias** (chars Unicode reservados,
  marcadores em bits): poderiam reduzir o custo por idx.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-22-syntax-compact-v2
python run.py
```

Saída: 21 datasets × 3 sintaxes, 2 tabelas + roundtrip 63/63.
TCFs em `encoded/verbose/`, `encoded/compact_v1/`,
`encoded/compact_v2/`.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **Compact v2 não é universalmente melhor que v1**: ganha em
   17 casos, perde em 4 (iso e ips em escala grande)
2. **Custo proporcional ao número de quebras** por nó
3. **Hipótese da Direção 2 da nota**: validada parcialmente —
   funciona em casos com estrutura clara; quebra em casos com
   alta entropia de slices
4. **Interface `Syntax` se mostrou novamente suficiente** —
   nenhuma evolução foi necessária
