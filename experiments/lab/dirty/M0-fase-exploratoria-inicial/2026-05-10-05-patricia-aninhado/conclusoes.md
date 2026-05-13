# Conclusões — TCF aninhado lado a lado

Roundtrip OK em **4/4 cenários**.

## D1 — sem prefixo (controle)

Patricia inativo. Nenhuma decl aninhada. Output igual ao que seria
no exp 03 normalizado.

```
no1: 2x folha "Ana"
no2: folha "Bob"
no3: folha "Carlos"
ref:no1
ref:no2
no4: folha "Diana"
ref:no3
no5: folha "Edu"
... (refs subsequentes)
```

Validação: o algoritmo aninhado degrada graciosamente quando não há
Patricia — não cria aninhamento desnecessário.

## D2 — um prefixo profundo (Mar / Marc)

Árvore Patricia tem 2 níveis internos:

```
no7 = "Mar"
  no1 = pai(no7) + "ina"  -> "Marina"
  no6 = pai(no7) + "c"  -> "Marc"
    no3 = pai(no6) + "io"  -> "Marcio"
    no4 = pai(no6) + "elo"  -> "Marcelo"
no2 = "Bob"
no5 = "Ana"
```

(Numeração da árvore é a interna do `patricia.py`; os eids do TCF
abaixo são reatribuídos pela ordem de aparição no body.)

TCF aninhado:

```
no1: filho_de(no2=decl folha "Mar") + "ina"
no3: folha "Bob"
no4: filho_de(no5=decl filho_de(no2) + "c") + "io"
ref:no1
no6: filho_de(no5) + "elo"
no7: folha "Ana"
... (refs)
```

Leitura linha a linha:

- **Linha 1**: Marina é a 1ª no body. Recebe `no1`. Seu pai `Mar`
  ainda não existe → embutido como `no2=decl folha "Mar"` dentro da
  decl de Marina.
- **Linha 2**: Bob, folha simples, recebe `no3`.
- **Linha 3**: Marcio é a 3ª string nova. Recebe `no4`. Seu pai
  `Marc` ainda não existe → embutido como `no5=decl filho_de(no2) + "c"`.
  Note que **dentro da decl aninhada de Marc** já há uma ref para
  `no2` (Mar, declarado na linha 1). **Cadeia recursiva**: decl
  aninhada de pai que depende de outra decl já feita.
- **Linha 4**: 2ª ocorrência de Marina → ref simples.
- **Linha 5**: Marcelo. Seu pai `Marc` (no5) já foi declarado
  dentro da linha 3 → ref simples `filho_de(no5)`.
- **Linha 6**: Ana, folha simples, recebe `no7`.

Comportamento confirmado: nenhuma decl tardia no fim. Todas as 7
decls de nó estão embutidas no body, dentro da primeira linha que
precisa de cada uma.

## D3 — hierárquico raso (USR000)

Apenas 1 nível Patricia interno:

```
no6 = "USR000"
  no1 = pai(no6) + "1"
  ...
  no5 = pai(no6) + "5"
```

TCF:

```
no1: filho_de(no2=decl folha "USR000") + "1"
no3: filho_de(no2) + "2"
ref:no1
no4: filho_de(no2) + "3"
ref:no1
no5: filho_de(no2) + "4"
ref:no3
ref:no1
no6: filho_de(no2) + "5"
... (refs)
```

Aqui só a 1ª linha (USR0001) embute o pai. Todas as outras
declarações de USR000X (no3, no4, no5, no6) usam `filho_de(no2)`
diretamente.

## D4 — duas famílias separadas (Mar e Paul)

Árvore:

```
no7 = "Mar"
  no1 = pai(no7) + "ina"
  no3 = pai(no7) + "cio"
no6 = "Paul"
  no2 = pai(no6) + "inho"
  no4 = pai(no6) + "a"
no5 = "Bob"
```

TCF:

```
no1: filho_de(no2=decl folha "Mar") + "ina"
no3: filho_de(no4=decl folha "Paul") + "inho"
no5: filho_de(no2) + "cio"
no6: filho_de(no4) + "a"
no7: folha "Bob"
... (refs)
```

Duas decls aninhadas **independentes** — cada uma na 1ª folha do
seu prefixo. Marcio (no5) usa `filho_de(no2)` direto, porque Mar
(no2) já foi declarado dentro de Marina (no1). Paula (no6) usa
`filho_de(no4)` direto, porque Paul (no4) já foi declarado dentro
de Paulinho (no3).

## Pontos a registrar

1. **Roundtrip 4/4 OK**. Decoder reconstrói todas as 30 linhas de
   cada cenário corretamente.

2. **Decode em 1 passada** (vs 2 passadas no exp 03/04). Forward
   refs não são necessárias porque toda decl aparece antes (ou no
   mesmo ponto) de ser referenciada como ref simples.

3. **Cadeia recursiva funciona**: D2 mostra
   `no4: filho_de(no5=decl filho_de(no2) + "c") + "io"`. A decl
   aninhada de no5 (`Marc`) referencia no2 (`Mar`) que foi
   declarado na linha anterior. Profundidade arbitrária é suportada
   pelo algoritmo.

4. **Algoritmo degrada graciosamente** em D1 (sem Patricia): sem
   aninhamento, output igual ao exp 03 normalizado.

5. **Numeração por ordem de aparição** continua sendo o esquema —
   tanto para folhas quanto para pais que são declarados aninhados.
   `no1, no2, ...` na ordem em que `get_eid` é chamada pela
   primeira vez, incluindo dentro de decls aninhadas.

## O que este experimento NÃO mostra

- Comparação numérica de bytes com exp 03/04 (datasets diferentes).
- Comportamento em N grande (apenas 30 linhas por cenário).
- Comportamento com hierarquias Patricia muito profundas (4+
  níveis).
- Otimização da numeração de eids — `no1, no2, ...` é ordem de
  invocação, não a numeração mais eficiente.
- Performance do parser (decode em 1 passada, mas chamadas
  recursivas de profundidade igual à árvore).
- Alternativas de sintaxe para a decl aninhada (`=decl`,
  delimitadores, indentação). Apenas a forma do user foi testada.
