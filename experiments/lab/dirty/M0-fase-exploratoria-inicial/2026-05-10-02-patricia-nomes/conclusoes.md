# Conclusões — comportamento observado

Linguagem descritiva. Sem juízo "melhor/pior", sem extrapolar para
outros cenários.

## Cenário A — nomes simples (50 linhas, cardinalidade 5)

Input: `Ana, Bob, Carlos, Diana, Edu` em mistura com runs e dispersão.

### Árvore final

```
no1 = "Ana"
no2 = "Bob"
no3 = "Carlos"
no4 = "Diana"
no5 = "Edu"
```

5 nós top-level. **Nenhum filho Patricia**.

### Por que Patricia não fatorou

Os 5 nomes não compartilham prefixo de ≥ 3 chars com pelo menos
2 ocorrências. `Ca` (de `Carlos`) tem só 1 ocorrência; `Bob`/`Bob`
não geram prefixo próprio na coleção (são string completa, não
prefixo). A heurística rejeita corretamente.

Comportamento observado: **Patricia degrada para uma DICT simples
quando não há prefixo comum**. O algoritmo não força fatorização.

### Body com RLE adjacente

Body bruto: 50 entradas (uma por linha).
Body após RLE: 33 entradas.
Runs com rep > 1: 14.

Trecho do body:

```
2x ref:no1     <- Ana, Ana
ref:no2        <- Bob
ref:no1        <- Ana
2x ref:no2     <- Bob, Bob
3x ref:no3     <- Carlos, Carlos, Carlos
ref:no4        <- Diana
2x ref:no1     <- Ana, Ana
...
```

Runs adjacentes do CSV original viraram entradas únicas. Linhas que
não eram adjacentes ao mesmo valor permaneceram como entradas
individuais (rep=1).

Observação: **RLE adjacente emergiu naturalmente da serialização**
porque o body é a sequência das linhas e o algoritmo agrupa
adjacentes idênticos. Não foi necessária análise extra para detectar
runs.

## Cenário B — identificadores hierárquicos (30 linhas, 15 únicos)

Input: 10 valores `USR0001..USR0010` + 5 valores `PRD0001..PRD0005`,
misturados.

### Árvore final

```
no17 = "PRD000"
  no3  = pai(no17) + "1"  -> "PRD0001"
  no5  = pai(no17) + "2"  -> "PRD0002"
  no9  = pai(no17) + "3"  -> "PRD0003"
  no12 = pai(no17) + "4"  -> "PRD0004"
  no15 = pai(no17) + "5"  -> "PRD0005"

no18 = "USR00"
  no14 = pai(no18) + "10"  -> "USR0010"
  no16 = pai(no18) + "0"   -> "USR000"
    no1  = pai(no16) + "1"  -> "USR0001"
    no2  = pai(no16) + "2"  -> "USR0002"
    no4  = pai(no16) + "3"  -> "USR0003"
    no6  = pai(no16) + "4"  -> "USR0004"
    no7  = pai(no16) + "5"  -> "USR0005"
    no8  = pai(no16) + "6"  -> "USR0006"
    no10 = pai(no16) + "7"  -> "USR0007"
    no11 = pai(no16) + "8"  -> "USR0008"
    no13 = pai(no16) + "9"  -> "USR0009"
```

18 nós no total: 2 top-level (`USR00`, `PRD000`), 16 filhos.
Profundidade até 3 níveis em `USR0001..USR0009` (pai → filho → neto).

### Como Patricia chegou nesta forma

Algoritmo é guloso iterativo. Sequência observada (mais detalhe em
[algoritmo.md](algoritmo.md)):

1. **Iteração 1**: escolheu prefixo `"USR000"` (len 6, 9 folhas).
   Fatorou `USR0001..USR0009` para terem pai = nó novo `USR000`.
   `USR0010` ficou top-level (não começa com `"USR000"` — começa
   com `"USR001"`).
2. **Iteração 2**: escolheu `"PRD000"` (len 6, 5 folhas). Fatorou
   `PRD0001..PRD0005`.
3. **Iteração 3**: top-levels agora são `USR000` (nó), `USR0010`,
   `PRD000` (nó). Prefixo comum entre `USR000` e `USR0010` é
   `"USR00"` (len 5). Criou pai novo `USR00`, ambos viraram filhos
   dele. `USR000` que era top-level virou filho intermediário.
4. **Iteração 4**: nada mais qualifica → parou.

A árvore não é "ótima global" (uma análise estática poderia produzir
outra forma). É **o resultado da heurística gulosa** sob `MIN_PREFIXO=3,
MIN_GRUPO=2`.

### Fato curioso

`USR0010` ficou em `USR00` direto com sufixo `"10"`, **não** em
`USR000` com sufixo `"10"`. Isso é correto em string: `"USR00" + "10"`
reconstrói `"USR0010"`. Mas mostra que Patricia não tem noção
"semântica" de que `USR0010` é o décimo da série; trata como mais
uma string com prefixo comum parcial.

### Body com RLE adjacente

Body bruto: 30 entradas.
Body após RLE: 20 entradas.
Runs com rep > 1: 9.

Trecho:

```
2x ref:no1     <- USR0001, USR0001
ref:no2        <- USR0002
2x ref:no3     <- PRD0001, PRD0001
3x ref:no4     <- USR0003 (3 vezes adjacente)
...
```

### Roundtrip

`decoded == input` → OK. 30 strings reconstruídas idênticas ao CSV.

## Pontos a registrar

1. **Patricia produziu hierarquia recursiva** sob a heurística
   gulosa: o nó `USR000` foi criado top-level na iter 1, depois virou
   filho do nó `USR00` na iter 3 — sem que seu id mudasse, sem
   quebrar refs no body.

2. **Patricia não fatorou em A**: comportamento esperado dado o
   parâmetro `MIN_PREFIXO=3` e a ausência de prefixos comuns
   significativos entre `Ana, Bob, Carlos, Diana, Edu`. A árvore
   degrada para uma DICT simples sem custo extra.

3. **RLE adjacente emerge naturalmente** da serialização do body
   porque o body preserva a ordem das linhas. Em ambos os cenários
   houve runs (14 em A, 9 em B). RLE não é "ganho de Patricia" — é
   propriedade independente da camada de body.

4. **Patricia e RLE são camadas ortogonais** neste experimento:
   - Patricia atua no inventário de strings únicas (`<patricia>`).
   - RLE atua na sequência de ocorrências (`<body>`).
   Em A, Patricia ficou inativa e RLE atuou sozinho. Em B, ambos
   atuaram. Os dois números (nós, RLE runs) variam de forma
   independente.

5. **Roundtrip OK** nos 2 cenários valida que a serialização
   demonstrativa é completa: o decode reconstrói as strings via
   cadeia pai+sufixo + expansão de RLE, sem perda.

## O que este experimento NÃO mostra

- Comportamento em cardinalidade > 15.
- Comportamento com prefixos sobrepostos parciais (ex: `USR000` e
  `USRN00` coexistindo).
- Bytes economizados em comparação a outros formatos. Marcadores
  verbosos inflam o TCF (624 e 901 bytes); a comparação de bytes
  pertence a um experimento posterior com formato compacto.
- Parametrização: `MIN_PREFIXO=3` e `MIN_GRUPO=2` foram fixados sem
  varredura.
- Robustez do parser do decode contra inputs malformados.
