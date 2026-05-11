# Hipóteses de COMPRESSÃO (sem cabeçalho, sem manifest, só transformação dos dados)

Cada hipótese é uma transformação do mesmo conjunto. Sem header. Sem manifest.
Só o que o dado vira na hora de escrever.

> **Nota sobre bytes:** contagem feita à mão considerando UTF-8 (`João`=5B, `Lápis`=6B,
> `Régua`=6B etc.) com `\n` (1B) como separador. São aproximações para sentir
> ordens de grandeza — verifique e ajuste se quiser precisão exata.

---

## C1 — Row-major literal (baseline tipo CSV)

Mantém ordem original, linha a linha. É o CSV de partida.

```
nome, produto, quantidade, valor_unitario
João, Caneta, 10, 1.50
João, Caderno, 5, 3.00
Maria, Caneta, 10, 1.50
Maria, Caderno, 5, 3.00
Ana, Caderno, 5, 3.0
Maria, Lápis, 20, 0.50
Carlos, Caneta, 10, 1.50
Carlos, Caderno, 5, 3.0
Ana, Régua, 8, 2.00
Ana, Borracha, 15, 0.75
Carlos, Régua, 8, 2.00
João, Régua, 8, 2.00
```

**Bytes:** ≈324  
**Comentário:** baseline absoluto. Cada linha repete `, ` 3× (6B de delimitador
por linha × 12 linhas = 72B só de pontuação). Sem nenhuma exploração de
repetição.

---

## C2 — Column-major literal

Transpõe: cada coluna listada inteira antes da próxima. Ordem original preservada.

```
nome:
João
João
Maria
Maria
Ana
Maria
Carlos
Carlos
Ana
Ana
Carlos
João
produto:
Caneta
Caderno
Caneta
Caderno
Caderno
Lápis
Caneta
Caderno
Régua
Borracha
Régua
Régua
quantidade:
10
5
10
5
5
20
10
5
8
15
8
8
valor_unitario:
1.50
3.00
1.50
3.00
3.0
0.50
1.50
3.00
2.00
0.75
2.00
2.00
```

**Bytes:** ≈294 (-9% vs C1)  
**Comentário:** ganho vem só de eliminar os `, ` repetidos. Nenhuma compressão
real ainda — só rearranjo do layout. É o "L0 verdadeiro" do TCF.

---

## C3 — Column-major + RLE local (sem reordenar)

Aplica RLE apenas em sequências adjacentes que já estão juntas na ordem original.
Não reordena nada.

```
nome:
2*João
2*Maria
Ana
Maria
2*Carlos
2*Ana
Carlos
João
produto:
Caneta
Caderno
Caneta
2*Caderno
Lápis
Caneta
Caderno
Régua
Borracha
2*Régua
quantidade:
10
5
10
2*5
20
10
5
8
15
2*8
valor_unitario:
1.50
3.00
1.50
3.00
3.0
0.50
1.50
3.00
2.00
0.75
2*2.00
```

**Bytes:** ≈260 (-12% vs C2, -20% vs C1)  
**Quantos `N*valor` apareceram?** 9 runs (4 em nome, 1 em produto, 2 em
quantidade, 1 em valor) — mas só 5 economizam bytes. RLE de `N*5\n` (4B) tem
mesmo tamanho que `5\n5\n` (4B), então runs curtos de valor curto não rendem.  
**Comentário:** RLE local depende muito da sorte da ordem fonte. Aqui o nome
estava parcialmente agrupado (João,João, Maria,Maria, etc.) por acaso —
poderia não estar.

---

## C4 — Column-major + sort por `nome` + RLE

Reordena todas as linhas por `nome` (lex), aplica RLE.

```
nome:
3*Ana
3*Carlos
3*João
3*Maria
produto:
Caderno
Régua
Borracha
Caneta
Caderno
Régua
Caneta
Caderno
Régua
Caneta
Caderno
Lápis
quantidade:
5
8
15
10
5
8
10
5
8
10
5
20
valor_unitario:
3.0
2.00
0.75
1.50
3.0
2.00
1.50
3.00
2.00
1.50
3.00
0.50
```

**Bytes:** ≈255 (-13% vs C2, -21% vs C1)  
**Comentário:** RLE comeu o nome inteiro (4 runs perfeitos = 30B no total),
mas as outras colunas perderam toda chance de RLE — porque sort por nome
embaralha a ordem natural de produto/quantidade/valor. Trade clássico: um
ganho local destrói outro.

---

## C5 — Column-major + sort por `produto` + RLE

Mesma coisa, chave de ordenação é `produto`.

```
nome:
Ana
João
Maria
Ana
Carlos
João
Maria
Carlos
Maria
Ana
Carlos
João
produto:
Borracha
4*Caderno
3*Caneta
Lápis
3*Régua
quantidade:
15
4*5
3*10
20
3*8
valor_unitario:
0.75
2*3.00
2*3.0
3*1.50
0.50
3*2.00
```

**Bytes:** ≈212 (-28% vs C2, -35% vs C1)  
**Comentário:** O grande salto. Sort por produto **propaga RLE para 3 das 4
colunas** porque produto, quantidade e valor_unitario são perfeitamente
correlacionados nesse dataset (cada produto tem preço/qtd fixos). Só nome
sobra sem RLE — e nome só perde, porque embaralha. Insight: a coluna ideal
para sort é a que tem mais correlação com as outras.

Observação chata: `2*3.00` + `2*3.0` em vez de `4*3.00`. Os strings são
diferentes, RLE não funde. Normalização (3.0 → 3.00) seria pré-passo do
encoder, fora do escopo do formato.

---

## C6 — Column-major + group por `produto` (sem sort completo) + RLE

Agrupa contiguamente sem ordenação alfabética estrita. A ordem entre grupos
segue a primeira aparição no fonte: Caneta (row 0), Caderno (row 1), Lápis
(row 5), Régua (row 8), Borracha (row 9).

```
nome:
João
Maria
Carlos
João
Maria
Ana
Carlos
Maria
Ana
Carlos
João
Ana
produto:
3*Caneta
4*Caderno
Lápis
3*Régua
Borracha
quantidade:
3*10
4*5
20
3*8
15
valor_unitario:
3*1.50
2*3.00
2*3.0
0.50
3*2.00
0.75
```

**Bytes:** ≈212 (mesmo que C5)  
**Diferença observada de C5?** **Zero em compressão.** Os mesmos runs de RLE
aparecem nas mesmas colunas. A diferença é só *qual produto vem primeiro* na
ordem entregue. Isso vai importar muito quando entrar a quebra (B6) — a
ordem dos grupos define qual chunk vai primeiro pela rede.  
**Comentário:** sort vs group são equivalentes para compressão; a escolha é
sobre **ordem de entrega**, não tamanho.

---

## C7 — Column-major + sort por `valor_unitario` + RLE

Ordenação numérica (não lexicográfica). Stable sort dentro de empates.

```
nome:
Maria
Ana
João
Maria
Carlos
Ana
Carlos
João
João
Maria
Ana
Carlos
produto:
Lápis
Borracha
3*Caneta
3*Régua
4*Caderno
quantidade:
20
15
3*10
3*8
4*5
valor_unitario:
0.50
0.75
3*1.50
3*2.00
2*3.00
2*3.0
```

**Bytes:** ≈212 (mesmo que C5/C6)  
**Comentário:** mesma compressão de C5/C6 porque produto e valor_unitario
são bijetivos nesse dataset (mesma cardinalidade, perfeitamente
correlacionados). Em datasets onde valor varia dentro do mesmo produto
(promoções, regiões, etc.), C7 e C5 divergiriam. Aqui são equivalentes.

A escolha entre C5/C6/C7 é só sobre **qual coluna fica visualmente "perfeita"**
(com runs limpos: produto em C5/C6, valor em C7) — útil para LLM ler ou
para ordem de entrega.

---

## C8 — Column-major + dict por coluna (sem sort, sem RLE)

Cada coluna ganha seu próprio dicionário; valores no corpo viram índices.

```
# dict nome: João, Maria, Ana, Carlos
# dict produto: Caneta, Caderno, Lápis, Régua, Borracha
# dict quantidade: 10, 5, 20, 8, 15
# dict valor_unitario: 1.50, 3.00, 3.0, 0.50, 2.00, 0.75
nome:
0
0
1
1
2
1
3
3
2
2
3
0
produto:
0
1
0
1
1
2
0
1
3
4
3
3
quantidade:
0
1
0
1
1
2
0
1
3
4
3
3
valor_unitario:
0
1
0
1
2
3
0
1
4
5
4
4
```

**Bytes:** ≈329 (+12% vs C2, **+2% vs C1**)  
**Comentário:** **dict isolado é anti-compressivo nesse tamanho.** Custo do
dict (cabeçalhos `# dict ...` + valores únicos = ~190B) supera economia do
corpo (4×24=96B vs 4×~63=251B). Para dataset pequeno, dict só ganha quando
combinado com sort+RLE em outras colunas (próximo).

Nota técnica curiosa: as colunas `produto` e `quantidade` têm o **mesmo
vetor de índices** (`0,1,0,1,1,2,0,1,3,4,3,3`). Reflexo direto da
correlação produto↔quantidade. Em teoria, dict global de "produto" poderia
servir as duas (campo único, dois índices iguais). Não testado aqui.

---

## C9 — Pilha completa: sort + RLE + dict

Aplica C5 (sort produto + RLE), depois adiciona dict só em `nome` (coluna
sem RLE útil).

```
# dict nome: Ana, João, Maria, Carlos
nome:
0
1
2
0
3
1
2
3
2
0
3
1
produto:
Borracha
4*Caderno
3*Caneta
Lápis
3*Régua
quantidade:
15
4*5
3*10
20
3*8
valor_unitario:
0.75
2*3.00
2*3.0
3*1.50
0.50
3*2.00
```

**Bytes:** ≈206 (-30% vs C2, -36% vs C1, -3% vs C5)  
**Comentário:** dict aplicado só onde RLE não funcionou — ganho marginal de
6B sobre C5. Dict de nome custa 39B (dict line) mas economiza 45B no corpo
(69B → 24B). Em dataset maior (mais linhas, mesma cardinalidade), o dict
amortiza melhor — aqui mal vale a pena.

**Hipótese para escala:** o ganho de C9 sobre C5 cresce linearmente com o
número de linhas (cada linha adicional do nome paga 4-6B literal vs 2B
indexado), enquanto o custo do dict é fixo. Em N=100 linhas, C9 venceria C5
por uma margem clara.

---

## C10 — Variante: dict IMPLÍCITO por sequência (sobre C7 ordenado)

Diferente do C8 (dict explícito em bloco separado), aqui a primeira ocorrência
do valor já é a definição do índice. Repetições posteriores referenciam só pelo
índice. Não precisa de bloco `# dict ...` antes.

**Notação proposta:**
- `1:Maria` → "este valor é Maria, e fica registrado como índice 1"
- `1:` → "este valor é o índice 1 (Maria)"
- O `:` é o discriminador. `1:` sem valor = referência; `1:X` = declaração.

Aplicado às 4 colunas de C7 (sorted by valor_unitario):

```
nome:
1:Maria
2:Ana
3:João
1:
4:Carlos
2:
4:
3:
3:
1:
2:
4:
produto:
1:Lápis
2:Borracha
3:Caneta
3:
3:
4:Régua
4:
4:
5:Caderno
5:
5:
5:
quantidade:
1:20
2:15
3:10
3:
3:
4:8
4:
4:
5:5
5:
5:
5:
valor_unitario:
1:0.50
2:0.75
3:1.50
3:
3:
4:2.00
4:
4:
5:3.00
5:
6:3.0
6:
```

**Bytes:** ≈270 (-8% vs C2, -17% vs C1)  
**Comentário:** ganha do literal (C2=294) e do dict explícito (C8=329), mas
**perde do RLE pós-sort** (C7=212). Por quê? RLE expressa contiguidade em
forma muito compacta (`3*Caneta` = 9B); dict implícito gasta uma linha por
repetição (`3:` = 3B cada). Para 3 repetições contíguas: RLE = 9B, dict
implícito = 9+3+3 = 15B.

### Onde C10 brilha (e RLE não)

A vantagem real do dict implícito aparece quando os valores **repetem de
forma espalhada, não contígua**. Em C7, a coluna `nome` não tem nenhum
adjacente igual (RLE = 0 ganho); mesmo assim o C10 economiza ~14B em nome
porque captura ocorrências distantes.

| Coluna em C7 | Repete contíguo? | RLE ganho | Dict implícito ganho |
|---|---|---|---|
| nome | não | 0B | ~14B |
| produto | sim | ~46B | ~21B |
| quantidade | sim | ~10B | -15B (perdeu!) |
| valor_unitario | sim | ~26B | ~4B |

→ Insight: **RLE e dict implícito são complementares**, não substitutos. RLE
domina quando há contiguidade; dict implícito domina quando há repetição
espalhada. Um encoder esperto poderia escolher por coluna.

### Combinação possível (não testada): C10 + RLE sobre referências

Para colunas onde tem contiguidade *de referências* (ex: `3:` `3:` `3:`),
poderia aplicar RLE sobre o índice:

```
3:Caneta
2*3:        ← "duas vezes a referência ao índice 3"
```

Isso recuperaria o ganho que C10 perde para o RLE puro. Vira um L4 híbrido.
Reservar para experimento separado depois que o C10 puro estiver validado.

### Risco de notação

A notação `N:` é ambígua se houver valor literalmente igual a `N:` no
dataset (improvável mas possível). Solução: regra "se primeira aparição
tinha valor, futuras `N:` sem valor são referência; senão, valor literal".
O parser precisa carregar essa tabela enquanto lê — barato, mas não é
livre.

Outra alternativa: prefixo explícito (`@1`, `^1`, `&1`) que nunca colide
com dado. Mais robusto mas mais longo. Trade-off para discutir.

---

## C11 — Dict implícito com discriminador AUTO por coluna

Refinamento de C10: o `:` só aparece quando é necessário para distinguir
referência de valor literal. Em colunas onde valores não colidem com inteiros
puros, o índice fica **só o número, sem nada**.

### Regra de exclusão (encoder decide por coluna)

| Domínio dos valores | Referência usa | Por quê |
|---|---|---|
| Nenhum valor é inteiro puro (`Maria`, `1.50`) | bare integer (`1`, `2`, `3`) | parser sabe que `1` não pode ser valor |
| Algum valor é inteiro puro (`5`, `10`, `20`) | marcado (`:1` ou `&1`) | bare colidiria com literal |
| Valores numéricos com decimal (`1.50`, `0.75`) | bare integer | `1` ≠ `1.50`, sem colisão |

A escolha é por **coluna**, não pelo arquivo todo.

### Aplicado a C7 (sort por valor_unitario)

```
nome:
Maria
Ana
João
1
Carlos
2
4
3
3
1
2
4
produto:
Lápis
Borracha
Caneta
3
3
Régua
4
4
Caderno
5
5
5
quantidade:
20
15
10
:3
:3
8
:4
:4
5
:5
:5
:5
valor_unitario:
0.50
0.75
1.50
3
3
2.00
4
4
3.00
5
3.0
6
```

Notas sobre cada coluna:
- **nome:** todos não-inteiros → bare. `1` claramente não é nome.
- **produto:** mesmo caso → bare.
- **quantidade:** valores `5`, `8`, `10`, `15`, `20` são inteiros puros e
  colidem com índices `1..5`. **Precisa marcador.** Usei `:3` (índice à
  direita do colon) para que valor literal fique sem prefixo.
- **valor_unitario:** todos têm decimal (`0.50`, `1.50`, `3.0`) → `1` não
  colide com nenhum literal → bare funciona.

### Bytes por coluna (C11 implícito puro, sem RLE)

| Coluna | C7 literal | C10 com `:` | C11 bare/marcado | Vencedor |
|---|---|---|---|---|
| nome | 69 | 55 | **39** | C11 |
| produto | 90 | 69 | **52** | C11 (entre dict, mas RLE=44 vence) |
| quantidade | 29 | 44 | 35 | C7 RLE (=19) ainda vence |
| valor_unitario | 63 | 59 | 41 | C7 RLE (=37) ainda vence |

**C11 total puro:** 43 + 39 + 52 + 35 + 41 = **≈210 bytes** (-29% vs C2, -35% vs C1)

Já empata com C5/C6/C7 (212B) sem fazer nenhum sort. Apenas dict implícito
adaptativo na ordem original já é competitivo com sort+RLE.

### C11-híbrido (encoder escolhe melhor representação por coluna)

A real força aparece se o encoder, depois de sort por produto/valor (C7),
escolher dict implícito para nome (que não tem RLE útil) e RLE para os outros:

```
nome (bare dict implícito, em ordem C7):
Maria
Ana
João
1
Carlos
2
4
3
3
1
2
4
produto (RLE pós-sort):
Lápis
Borracha
3*Caneta
3*Régua
4*Caderno
quantidade (RLE pós-sort):
20
15
3*10
3*8
4*5
valor_unitario (RLE pós-sort):
0.50
0.75
3*1.50
3*2.00
2*3.00
2*3.0
```

**C11-híbrido total:** 43 + 39 + 44 + 19 + 37 = **≈182 bytes** (-44% vs C1, -14% vs C9)

**Novo recorde do conjunto.** Ganha de C9 (206B) porque elimina a linha de
dict explícita (`# dict nome: ...` = 39B) sem perder nada — a primeira
aparição do nome serve como declaração natural.

### Por que C11 é melhor que C9 estruturalmente

- **C9:** dict separado em bloco no header, corpo só com índices.  
  Custo: linha de prefixo (`# dict ...`) + valores únicos listados juntos.
- **C11:** dict construído inline conforme aparece. Primeira ocorrência
  carrega o valor; seguintes só o índice.  
  Vantagem: zero overhead de header de dicionário; o "dicionário" é só uma
  visão emergente do corpo conforme se lê.

### Implicação para o decoder

O decoder precisa manter um pequeno mapa enquanto lê cada coluna:
- Vê valor literal pela primeira vez → atribui próximo índice (1, 2, 3...)
  e armazena
- Vê inteiro/`:N` que combina com índice já visto → resolve
- Termina coluna → descarta o mapa (ou guarda para auditoria)

Custo: O(cardinalidade da coluna) de memória local. Para o dataset todo:
mesma ordem de grandeza que C8/C9, só que o mapa não precisa ser
pré-declarado nem pré-carregado.

### Riscos e tickets futuros

1. **Modo de discriminação por coluna precisa estar legível** — ou o decoder
   detecta sozinho (varredura inicial), ou o header declara explicitamente
   (`encoding=bare`, `encoding=marked`). Decisão pendente.
2. **C11 + RLE sobre referências:** sequência `3 3 3` poderia virar `3*3`,
   mas isso é ambíguo (RLE de valor 3? três vezes a referência 3?).
   Notação alternativa: `3=3*` ou `(3)*3` ou similar. Reservar para teste.
3. **Em datasets grandes com cardinalidade alta**, índices viram 2-3 dígitos
   (`123`, `456`). Ainda compactam vs strings, mas o ganho marginal cai.
   Hipótese para validar com TPC-H real.

---

## C12 — Dict implícito com PROGNÓSTICO de frequência (e reciclagem de índice)

Refinamento de C11. Em vez de só declarar o índice na primeira aparição, a
declaração inclui **quantas vezes** o valor vai aparecer no total. Quando a
contagem se esgota, o índice fica livre para reciclar em outro valor.

### Princípios extraídos da proposta

| Notação | Semântica |
|---|---|
| `1:3xMaria` | Declara idx 1 = Maria, prevê **3** ocorrências totais (esta inclusa) |
| `1:xMaria`  | Declara idx 1 = Maria, prevê **1** ocorrência (única — `x` solto = "só essa") |
| `1`         | Referência ao idx 1; decrementa contagem prevista |
| `1:3x`      | Re-afirma idx 1 com **3** ocorrências adicionais (fluxo streaming) |
| (após esgotar) | Idx liberado; próximo `idx:NxValor` pode reusar o número |

### Aplicado ao nome de C7 (sorted by valor_unitario)

Contagens prévias (encoder em 1ª passada): Maria=3, Ana=3, João=3, Carlos=3
(coincidência neste dataset; em outros pode variar).

```
nome:
1:3xMaria
2:3xAna
3:3xJoão
1
4:3xCarlos
2
4
3
3      ← João esgotou, idx 3 livre
1      ← Maria esgotou, idx 1 livre
2      ← Ana esgotou, idx 2 livre
4      ← Carlos esgotou, idx 4 livre
```

### Bytes

| Linha | Bytes |
|---|---|
| `1:3xMaria\n` | 10 |
| `2:3xAna\n` | 8 |
| `3:3xJoão\n` | 10 |
| `1\n` | 2 |
| `4:3xCarlos\n` | 11 |
| `2\n` | 2 |
| `4\n` | 2 |
| `3\n` | 2 |
| `3\n` | 2 |
| `1\n` | 2 |
| `2\n` | 2 |
| `4\n` | 2 |
| **total** | **55** |

Comparação só na coluna nome:

| Variante | Bytes | vs C11 bare |
|---|---|---|
| C7 literal | 69 | +30 |
| C10 (com `:`) | 55 | +16 |
| **C11 bare** | **39** | **0** |
| C12 com prognóstico | 55 | +16 |

**No bytecount puro, C12 perde para C11.** O custo de carregar `Nx` em cada
declaração (~3-4B por valor único) supera qualquer ganho que a reciclagem
poderia trazer aqui — porque os 4 nomes coexistem o tempo todo nesse dataset.

### Onde C12 ganharia (cenários hipotéticos)

1. **Cardinalidade muito alta com simultaneidade baixa.**
   Ex: 1000 clientes ao longo do tempo, mas só ~5 "ativos" por janela. Sem
   reciclagem, índices viram `123`, `456`, `1023` (3-4 dígitos). Com
   reciclagem, índices ficam em `1..9` (1 dígito). Economia em cada
   referência.
2. **Streaming sem fim previsível.**
   `1:3x` re-afirmando "mais 3 vezes" permite que o encoder anuncie
   contagens parciais sem precisar conhecer o total antecipadamente.
3. **Decoder precisa pré-alocar buffer.**
   O `Nx` informa o tamanho exato — o decoder reserva slot certo, evita
   realocação. Custo em bytes, ganho em runtime.
4. **Verificação de integridade.**
   Encoder prometeu 3 Marias; decoder conta 3. Se vier 2 ou 4, sinal de
   corrupção — checksum semântico embutido grátis.

### Onde C12 perde (este caso)

- Todos os valores coexistem do início ao fim → reciclagem não acontece.
- Cardinalidade baixa (4 valores) → índices já caberiam em 1 dígito sem
  reciclagem.
- Sem streaming → contagem antecipada é só overhead.

### Ambiguidades a resolver

A proposta tem alguns pontos que precisam fechar antes de virar especificação:

1. **`x` solto = "uma vez só" ou "última ocorrência"?**
   No exemplo `3:xJoao` — é "será visto exatamente uma vez total"? Ou "esta
   é a última ocorrência" (já houve outras antes)?
   → Decisão proposta: **`x` solto significa N=1**. Para "encerrar índice no
   meio", basta a contagem se esgotar naturalmente.

2. **Pode haver mais ocorrências do que o prometido?**
   Encoder disse `2:3xAna` mas aparece uma 4ª Ana. O que faz?
   → Decisão proposta: **erro estrito** — encoder com bug, não o decoder
   que precisa tolerar. Validação determinística.

3. **Re-declaração `2:4x` (sem valor) recoloca o valor antigo no índice ou
   é só ajuste de contagem?**
   → Decisão proposta: **só ajuste de contagem**. Reuso para outro valor
   exige índice já esgotado e nova declaração `:Nxvalor`.

4. **Pode-se omitir o `N` quando = 1?** `3:xJoao` vs `3:1xJoao`.
   → Decisão proposta: **omissão é OK** — economiza 1B em valores únicos,
   que são frequentes em colunas de alta cardinalidade.

5. **Como o decoder distingue `1` (referência) de um valor literal `1` em
   coluna numérica?** Mesmo problema do C11 — resolve com regra de exclusão
   por coluna ou marcador `:N`.

### Comparação estrutural com C11

| Aspecto | C11 bare | C12 prognóstico |
|---|---|---|
| Overhead na 1ª aparição | 0 (só o valor) | +Nx prefixo |
| Tamanho do índice em alta cardinalidade | cresce (1→2→3 dígitos) | bounded por simultaneidade |
| Suporta streaming ilimitado | sim, mas índice cresce | sim, índice estável |
| Pré-alocação no decoder | não | sim |
| Verificação de integridade | não | sim |

→ **Conclusão**: C12 não é substituto de C11; é evolução para casos onde
**runtime > bytes**. Em datasets pequenos in-memory, C11 vence. Em streaming
de longa duração com alta cardinalidade rotativa, C12 vence.

### Combinação possível (não testada)

Encoder híbrido: aplica C11 por padrão; sobe para C12 quando detecta que
índice ultrapassaria 2 dígitos OU que a coluna está em modo streaming. O
header poderia declarar `nome encoding=dict-bare` ou `nome encoding=dict-counted`
por coluna.

### Onde isso deixa o ranking

C12 não muda o vencedor do dataset atual (C11-híbrido continua em ≈182B), mas
abre o caminho para um L4 adaptativo que escolhe entre C11/C12 conforme as
características da coluna em runtime. Esse é o bônus real da proposta — não
o byte-count imediato, mas o **espaço de design que ela abre** para encoders
inteligentes.

---

## Notas livres do teste de mesa

### O que apareceu repetidamente
- **Sort/group em coluna correlacionada com as outras** (C5/C6/C7) é o que
  realmente comprime nesse dataset. Tamanho final idêntico nos três; só a
  ordem de entrega muda.
- **RLE em valores curtos com runs curtos não economiza nada** — o `N*` ocupa
  o mesmo espaço que repetir o valor (vide quantidade em C3).
- **Dict isolado não compensa em datasets pequenos** (C8). Vira útil quando
  combinado com RLE seletivo (C9).
- **Strings "iguais mas diferentes"** (`3.00` vs `3.0`) impedem fusão de RLE
  e dict. Normalização é pré-encoder, não format.

### O que faltou explorar
- **Dict global compartilhado** (uma tabela serve várias colunas correlacionadas).
  Insight do C8: produto e quantidade têm vetores idênticos. Vale ticket separado.
- **Sort multi-coluna** (sort por produto, depois por nome): poderia dar runs
  de nome dentro de cada bloco de produto. Não testado.
- **Delta encoding em quantidade/valor** (5,8,15,10,5 → 5,+3,+7,-5,-5).
  Numérico, fora do escopo de RLE. Para dataset com timestamps ou IDs sequenciais
  seria interessante.

### Onde a quebra (próximo arquivo) vai morder
- Quem ganhou em compressão (C5/C6/C7/C9) vai perder se a quebra cortar no
  meio dos runs. Cada chunk vai ter que ter run-início e run-fim "limpos".
- A ordem de C6 (group, primeira aparição) parece a mais natural para casar
  com chunks por grupo (B4) — porque o "primeiro grupo no arquivo" é também
  o "primeiro grupo a chegar pela rede".
