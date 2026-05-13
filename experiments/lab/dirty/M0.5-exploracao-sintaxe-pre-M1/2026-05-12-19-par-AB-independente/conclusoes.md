# Conclusões — par A+B independente é equivalente em unidades

Roundtrip 21/21 OK. Resultado central: **a busca exaustiva não
trouxe ganho mensurável em unidades de informação** em nenhum
dos 21 datasets. Pior, em bytes verbosos chega a piorar 4-6% em
`codigos`.

## O que isso prova

O exp 16 (par com 1 âncora fixa, redução só na outra) já está
**perto do ótimo greedy** para o algoritmo "online sem revisão
com pref + meio + suf". A busca exaustiva sobre todos os pares
(prev_a, prev_b) confirma:

- Em 17/21 casos: cobertura, unidades e bytes **idênticos** ao
  exp 16
- Em 4/21 casos (`codigos` em todos os tamanhos): troca de
  estrutura sem mudança real em unidades

## O que muda em `codigos`

A heurística do exp 16 prefere `noN[0:13] + "X"` (1 ref grande +
literal curto). A busca exaustiva descobre alternativas como
`noN[0:3] + noM[-11:]` (2 refs, sem literal).

Ambas têm **2 unidades de informação**. Mas:

| Métrica | exp 16 | exp 19 |
|---|---|---|
| Unidades | 2 | 2 |
| Cobertura ref% | mais baixa | mais alta |
| Bytes verbosos | menor | maior |

A diferença está na **sintaxe verbosa** atual:

- `"X"` ocupa 3 chars (1 lit + 2 aspas)
- `noN[-K:]` ocupa 9 chars (3 + 4 brackets/dois pontos + dígitos)

Em **sintaxe compacta futura** (ver nota
[`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md)),
ref custaria 1-2 bytes e empataria com literal curto. Então o
trade-off bytes ↔ unidades **se diluiria**.

## Por que a busca exaustiva não revelou margem

A teoria estava certa em prever que pares A+B independentes
poderiam ajudar. Mas em datasets reais (mesmo sintéticos):

1. **Quando há overlap entre best_pref e best_suf**, a decisão
   conservadora do exp 16 (manter um, reduzir outro) já dá a
   melhor opção. Reduzir ambos não compensa o min_len que
   ambos têm.

2. **Quando não há overlap**, o melhor par é sempre
   `(best_pref, best_suf)` direto — não há vantagem em escolher
   pref/suf menores.

3. **O caso restante** (overlap + nenhuma das duas reduções dá
   cob = n) é raro nos datasets testados. Em quase todos os
   casos o exp 16 fecha a string sem deixar literal grande.

## Tempo: até 19× mais lento em escala

| Caso | t exp 19 | t exp 18 | razão |
|---|---:|---:|---:|
| iso-N1000 | 65.8 s | 3.4 s | **19.2×** |
| urls-N1000 | 11.0 s | 3.8 s | 2.9× |
| ips-N1000 | 1.1 s | 1.6 s | 0.68× (mais rápido por ruído) |
| codigos-N1000 | 0.9 s | 1.5 s | 0.61× |

`iso` foi o pior caso: as timestamps têm prefixos longos e sufixos
longos, então o produto cartesiano |prefs| × |sufs| é grande.

O custo é O(|prefs| × |sufs|) por string. Quando ambos são da
ordem de N, fica O(N³) total — viável até alguns milhares de
strings em Python, inviável acima.

## Direção descartada cientificamente

Este experimento **fecha a porta** para uma das direções
propostas no exp 15:

> "Limitações: O fix é conservador. Há combinações ainda não
> exploradas (ex: pref_id_A + suf_id_B onde A != B com tamanhos
> diferentes simultaneamente)."

Resposta: explorar essas combinações **não traz ganho em
unidades**. A heurística conservadora do exp 16 já cobre o que
era possível com essa estrutura.

Descartar uma direção é tão valioso quanto encontrar uma
melhoria. O caminho à frente fica mais claro: o gargalo real
**não está na escolha de par dada uma string**.

## Análise crítica dos "literais residuais" — não são defeito

Inspeção detalhada das categorias com literal nos TCFs gerados:

**ips-N1000 (2 só_literal):**

```
no1: "192.168.1.2"     ← 1ª string de todas (obrigatório)
no4: "10.0.5.41"       ← 1ª aparição da sub-rede 10.x.x.x
no6: "172.16.0.67"     ← 1ª aparição da sub-rede 172.x.x.x
```

Cada um é **primeira aparição** de uma sub-rede que não tinha
antecedente. Não há como referenciar informação que ainda não
existia.

**urls-N1000 (4 r+lit>4):**

```
no1:   "https://api.example.com/v1/users/00000/profile"   ← 1ª string
no335: no1[0:27] + "orders/2026-0000/items"               ← 1ª de orders
no668: no1[0:27] + "products/cat-a/sku-0000"              ← 1ª de products
no669: no668[0:40] + "b/sku-0001"                         ← 1ª de cat-b
no670: no668[0:40] + "c/sku-0002"                         ← 1ª de cat-c
```

Cada literal é **introdução de recurso ou categoria nova**. O
algoritmo já reaproveita a base URL e a categoria — só sobra o
pedaço genuinamente novo.

**codigos-N1000 (499 r+lit≤4):**

```
no5: no1[0:13] + "2"     ← introdução do serial "00002"
no9: no1[0:13] + "3"     ← introdução do serial "00003"
no6: no2[0:3] + no5[-11:]    ← INV-2026-00002 (puro ref, 0 lit)
```

Cada serial novo introduz 1 char novo (último dígito). Os outros
prefixos (INV/REQ/ORD) reaproveitam o sufixo do PED correspondente
sem literal.

## Conclusão revisada — o algoritmo está no ótimo

Os literais residuais **não são defeito**. São informação **inédita
no momento da emissão**:

- Em ips: novas sub-redes que aparecem primeira vez
- Em urls: novos recursos ou categorias
- Em codigos: novos seriais (1 char incremental)

Não há padrão emergindo tarde. Não há informação que esteja "lá"
e o algoritmo deixou passar. Cada literal é **dado novo**.

## Por que revisão retroativa NÃO ajudaria

A revisão retroativa atacaria a estrutura: reabrir um nó antigo
quando padrão emerge depois. Mas nos datasets do regime A:

- Para reescrever no335 (orders introdução), seria preciso que
  uma string posterior **revele** que `"orders/2026-0000/items"`
  podia ser ref a outra coisa. Mas o que vem depois (no336,
  no337, ...) são **refs a no335**, não fontes de novo padrão.
- O literal já está na fonte do padrão — reabri-lo só moveria
  o problema sem reduzir bytes.

A única coisa que reduziria seria **fatoração multi-nó**: criar
nó separado para `"orders/2026-"` quando 2+ orders aparecem. Mas
isso é outra estrutura (Patricia/grammar-based), não revisão
retroativa simples — e o ganho seria pequeno (1-5 nós em N=1000).

## Pontos a registrar

1. **Par A+B independente é equivalente em unidades** ao exp 16
   em todos os casos testados. Em sintaxe verbosa, chega a piorar
   bytes literais quando troca literal curto por ref.

2. **A busca exaustiva confirma**: a heurística do exp 16 é boa
   o suficiente para o regime "online + monotônico + pref+meio+suf".

3. **Os literais residuais NÃO são defeito** — são introduções
   genuínas de informação nova no momento da emissão. Inspeção
   caso a caso confirmou em urls, ips e codigos.

4. **Revisão retroativa não traria ganho** nesses datasets. Não
   há padrão emergindo tarde para ser capturado.

5. **Custo computacional do par A+B**: O(N³) total. Inviável em
   escala grande sem otimização.

6. **A diferença bytes ↔ unidades** observada em `codigos`
   reforça a importância da nota
   [`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md):
   bytes verbosos não são métrica fiel para comparar variantes
   estruturais.

## O que este experimento não mostra

- Comportamento em famílias não testadas
- Que o exp 16 é globalmente ótimo (apenas dentro das classes
  testadas em 21 datasets)
- Ganho potencial de fatoração multi-nó (Patricia/grammar)
- Ganho potencial de sintaxe compacta em bytes reais

## Próximas direções viáveis

Descartadas após este experimento:

- **Par A+B independente** (este exp): sem ganho
- **Revisão retroativa**: não atacaria literais que são
  introduções genuínas (análise acima)

Direções restantes com chance de ganho real:

- **Sintaxe compacta** (próxima): valida a hipótese da nota
  `marcadores-compactos` em bytes reais. Único caminho que pode
  reduzir bytes mantendo unidades. **Recomendado seguir aqui**.
- **Tipos com estrutura conhecida** (CPF, UUID, IP, ISO): única
  via para o regime B (uuids 0.7%, cpfs 0.0% no exp 17). Cada
  tipo é experimento separado.
- **Delta encoding** para `codigos`: o 1 char incremental por
  serial poderia virar `+1` (já estudado no lab arquivado
  `dirty/old/2026-05-09-delta-datas/`).
- **Fatoração multi-nó** (Patricia/grammar): criar nó separado
  para `"orders/2026-"`, `"products/cat-a/sku-"` etc. quando
  emergem. Custo de implementação alto, ganho marginal nos
  datasets atuais (4-5 nós em N=1000).
