# H1 — Multi-sort burro

Aplicando 6 combinações de chave múltipla. Para cada uma: encoder C11-híbrido
escolhe a melhor estratégia por coluna (RLE / dict-bare / literal).

---

## Sort (produto, valor)

Sub-sort por valor dentro de cada bloco de produto. Onde produto tem valor
único, sub-sort não muda nada. Onde tem múltiplos (Caneta, Caderno, Marcador):

- Caneta: 5×1.50 (rows 2,9,14,17,27), 2×2.00 (rows 5,23)
- Caderno: 4×3.00 (rows 4,7,20,25), 1×5.00 (row 13)
- Marcador: 4.00 (row 18), 4.50 (row 8)

### Bytes por coluna

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome (sem agrupar) | dict-bare | 98 |
| produto (8 runs perfeitos) | RLE | 79 |
| quantidade (runs locais melhores) | RLE-local | 61 |
| valor (runs por produto, mas 2.00 fragmenta entre Caneta e Régua) | RLE | 72 |
| headers | — | 43 |
| **total** | | **≈ 353 B** |

Observação: valor fragmenta — `2.00` aparece dentro de Caneta (×2) e Régua (×4)
em blocos separados. RLE produz `2*2.00` + `4*2.00` em vez de `6*2.00`. Custa
~3 B extras vs sort-by-valor único.

---

## Sort (valor, produto)

Sub-sort por produto dentro de cada bloco de valor. Efeito interessante:
nas fronteiras de bloco, alguns produtos **se concatenam** entre grupos de valor.

Exemplo crítico: valor 1.50 tem 5 Canetas; valor 2.00 começa com Caneta×2
(porque Caneta < Régua alfabético). Resultado: **Caneta×7 contíguo** atravessando
a fronteira de valor.

Outra fusão: valor 4.00 = Marcador, valor 4.50 = Marcador → **Marcador×2 contíguo**.

Trade: Caderno fragmenta (4×3.00 + 1×5.00 separados por Marcador).

### Bytes por coluna

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto (9 runs incluindo Caneta×7 e Marcador×2 fundidos) | RLE | 87 |
| quantidade (RLE local melhora mais) | RLE-local | 59 |
| valor (10 runs perfeitos, igual sort-valor) | RLE | 65 |
| headers | — | 43 |
| **total** | | **≈ 352 B** |

Sort-(valor, produto) **vence** sort-(produto, valor) por 1B, porque a fusão
de Caneta×7 e Marcador×2 mais que compensa a fragmentação de Caderno.

---

## Sort (produto, valor, quantidade)

Adiciona quantidade como 3º desempate. Afeta principalmente quantidade column,
que ganha mais runs locais.

### Bytes por coluna

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto (8 runs perfeitos) | RLE | 79 |
| quantidade (mais runs, ex: 4*10 dentro de Caneta) | RLE-local | 57 |
| valor (igual produto,valor) | RLE | 72 |
| headers | — | 43 |
| **total** | | **≈ 349 B** |

Ganho de qty: ~4B vs (produto, valor). Diminishing returns.

---

## Sort (valor, produto, quantidade)

Combinação que arrasta MÁXIMO de colunas. Adiciona qty como 3º desempate
dentro dos 6 blocos onde isso ainda faz diferença.

Resultado em qty: 4*10 (dentro de Caneta 1.50), 4*5 (dentro de Régua 2.00),
3*1 (50.00 + 5.00 boundary), etc.

### Bytes por coluna

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto (Caneta×7, Marcador×2 ainda fundidos) | RLE | 87 |
| quantidade (mais runs ainda) | RLE-local | 55 |
| valor | RLE | 65 |
| headers | — | 43 |
| **total** | | **≈ 348 B** |

**Vencedor da H1.** Sort-(valor, produto, qty) é o mais comprimido.

---

## Controles negativos

### Sort (nome, produto)

Nome fica perfeito (RLE 70). Produto sub-sortido alfabeticamente dentro de
cada nome — mas produtos por nome são quase todos distintos, então RLE em
produto saves ≈0.

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | RLE | 70 |
| produto | dict-bare (RLE = 0 saving) | 109 |
| quantidade | literal | 72 |
| valor | dict-bare | 93 |
| headers | — | 43 |
| **total** | | **≈ 387 B** |

Igual sort-by-nome solo. Sub-sort por produto não acrescenta nada. Confirma:
**sort secundário em coluna não-correlacionada é placebo.**

### Sort (produto, nome)

Produto perfeito (79). Nome sub-sortido por nome dentro de cada produto.
Coincidência: 1 par Diana/Diana adjacente (Borracha tem Diana e Gabriel/Helena;
sub-sort pode até criar essa colagem). Mas o padrão geral: nomes ficam scrambled.

≈ 379 B (essencialmente igual a sort-by-produto, ±1 B).

---

## Tabela mestre H1

| Sort | Bytes | Δ vs unordered (415) |
|---|---|---|
| (valor, produto, qty) | **348** | -67 |
| (produto, valor, qty) | 349 | -66 |
| (valor, produto) | 352 | -63 |
| (produto, valor) | 353 | -62 |
| (valor) — solo | 369 | -46 |
| (produto) — solo | 379 | -36 |
| (produto, nome) | 379 | -36 |
| (nome) — solo | 387 | -28 |
| (nome, produto) | 387 | -28 |
| Unordered | 415 | — |

---

## Achados de H1

### 1. Multi-sort em chaves correlacionadas ganha (pouco) sobre solo

Ganho marginal de adicionar 2ª chave: 16-17 B (sort solo → multi-sort).
Ganho marginal de 3ª chave: 4 B. Ganho marginal esperado de 4ª: <2 B.

**Diminishing returns rápido.** Acima de 3 chaves, custo cognitivo de
declarar a ordem provavelmente excede ganho.

### 2. Multi-sort em chave não-correlacionada é placebo

(nome, produto) e (produto, nome) deram resultados idênticos aos solos
correspondentes. Sub-sort em coluna que não correlaciona não move o byte.

### 3. A ordem das chaves importa, mas pouco

(produto, valor) = 353 vs (valor, produto) = 352. Diferença de 1 B vem da
fusão Caneta×5+×2=×7 que só acontece em valor-primeiro.

→ **Heurística:** colocar primeiro a chave que **mais fragmentaria sob o
sort solo** da segunda. No nosso caso: valor sob sort-produto fragmenta em 11
runs (ruim); produto sob sort-valor fragmenta em ~9 runs (melhor). Logo
valor-primeiro é melhor.

### 4. RLE+DICT pode ser sempre escolhido por critério

Empírico do dataset: RLE vence dict-bare quando a coluna tem ≥3 runs com
length ≥3 OU 1 run dominante (>50%). Caso contrário, dict vence. Caso
quantidade tenha valores numéricos puros sem run-dominante, literal vence
ambos.

Esse é um critério **decidível pelo encoder com 1 passada**:
- conta unicidade da coluna
- conta runs após sort proposto
- escolhe RLE se runs longos / dict se cardinalidade boa / literal se nem um
  nem outro

→ Resposta para pergunta da hipótese: **sim, é decidível por critério local
da coluna.**

---

## Limite teórico do multi-sort

Se sortarmos por TODAS as colunas (4 chaves), o resultado é uma ordem
totalmente determinística. Cada combinação única (nome, produto, qty, valor)
ganha 1 linha. Como aqui não há linhas duplicadas (são 30 distintas), todas
ficam lá, ordenadas em alguma ordem específica.

Isso NÃO ajuda mais que multi-sort de 3 chaves nesse dataset, porque a 4ª
chave é nome, que não correlaciona. Mas em datasets com **linhas duplicadas**
exatas, multi-sort completo permitiria RLE no nível da linha (`3*Ana,Caneta,10,1.50`)
em vez de RLE coluna-a-coluna. Esse é outro território — vale ticket separado.
