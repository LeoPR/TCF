# Conclusões — Re-Pair bottom-up

Roundtrip **3/3 OK**.

## Resultado central

| Dataset | exp 10 | exp 13 | delta |
|---|---:|---:|---:|
| D2-completo | 655 | **447** | **-208 (-31.8%)** |
| D4 | 505 | **424** | **-81 (-16.0%)** |

**Re-Pair venceu Patricia bidirecional em ambos os datasets
comparáveis**, mantendo roundtrip e usando sintaxe mais simples.

## Por que Re-Pair venceu

### (a) Sintaxe mais limpa

Comparação direta de uma linha do D2-completo:

| exp 10 | exp 13 |
|---|---|
| `no1: pref:(no2=decl folha "maria.silva@") + "g" + suf:(no3=decl folha "mail.com")` | `no1: (no2="maria.silva") + "@g" + (no3="mail.com")` |

`pref:` e `suf:` saíram. `decl folha` saiu. Sobra apenas
`(noN="X")` para decl aninhada e `noN` para ref. Cada linha
economiza ~10-15 chars.

### (b) Padrões "no meio" detectados

Re-Pair capturou `@yahoo.com` (10 chars, 4 strings) como
**símbolo único** em D2-completo. Patricia bidirecional do exp 10
não conseguia — tinha que decompor em `pref="ana.lima@"` (forward)
+ `mid="" + suf="@yahoo.com"` (reverse) com escolha entre eles via
heurística de overlap. Re-Pair vê `@yahoo.com` como uma única
substring frequente e fatora direto.

### (c) Padrões assimétricos capturados naturalmente

`maria.silva` (sem o `@`) virou símbolo em D2-completo. Em
algumas strings vai com `"@g"` depois, em outras com `"@hot"`. Re-Pair
escolheu a fronteira que dava maior gain, sem se prender a "tem que
ser prefixo até `@`". Patricia bidirecional não considera fronteiras
intermediárias.

### (d) Eliminação da árvore reverse

Re-Pair faz tudo numa única estrutura. Não há separação
"forward/reverse" — substring detecta naturalmente. Conforme você
intuiu: a árvore reverse perdeu sentido.

## Trecho TCF do D4 (lado a lado)

**Exp 10 (Patricia bidir, 505 bytes ref+dados):**
```
no1: pref:(no2=decl folha "https://api.example.com/v1/users/") + "1"
no3: pref:(no4=decl folha "https://api.example.com/v1/orders/10") + "0"
no5: pref:no2 + "2"
no7: pref:(no8=decl folha "https://api.example.com/v1/products/5") + "0"
...
```

**Exp 13 (Re-Pair, 424 bytes ref+dados):**
```
no1: (no2="https://api.example.com/v1/") + "users/1"
no3: no2 + (no4="orders/10") + "0"
no5: no2 + "users/2"
no6: no2 + no4 + "1"
no7: no2 + (no8="products/5") + "0"
...
```

Re-Pair fatorou a base URL (27 chars) **uma vez** como `no2`,
reaproveitada por todas as 12 strings. Em exp 10, a base era
duplicada 3 vezes (uma por recurso). Diferença ~50 bytes só por
isso.

## D2-completo — `ana.lima` ficou de fora

Re-Pair extraiu nesta ordem:
1. `mail.com` (gain 25, count 8)
2. `@yahoo.com` (gain 11, count 4)
3. `maria.silva` (gain 6, count 3)
4. `pedro.alves` (gain 6, count 3)
5. `joao.souza` (gain 6, count 3)

`ana.lima` apareceria em 4 strings com gain potencial ~5, mas
**não foi escolhido** — em iter 6 o algoritmo parou (verificar
critério ou comportamento residual). Resultado: `ana.lima` foi
duplicado em 4 strings como literal.

Se tivesse sido capturado: economia adicional ~5 chars. Pequeno.
Não muda a conclusão.

A heurística de stop tem espaço para ajuste — não impacta
estruturalmente, mas é nota a registrar.

## Pontos a registrar

1. **Re-Pair é mais simples e mais econômico** que Patricia
   bidirecional + composição nos cenários testados. Diferença
   considerável (16-32% em ref+dados).

2. **A árvore reverse não é necessária com Re-Pair** — substrings
   capturam padrões de borda e do meio uniformemente. Conforme sua
   intuição original.

3. **Sintaxe mais limpa** (`(no2="X")` para decl aninhada, `noN`
   para ref, `"X"` para literal, ` + ` entre tokens) elimina a
   distinção semântica `pref/suf` desnecessária para o decoder
   reconstruir.

4. **Decode em 1 passada**. Não precisa de forward refs nem decls
   tardias.

5. **Padrões assimétricos e do meio**: Re-Pair captura naturalmente
   (`@yahoo.com`, `mail.com`, `maria.silva`). Patricia bidir
   precisava de heurística complexa para algo equivalente, e ainda
   não cobria todos.

6. **Sintaxe ainda pode ser mais compacta**. As economias de
   31.8% / 16% foram com sintaxe verbosa. Marcadores compactos
   (`(N="X")`, ref `N`, sem `no` prefix) reduziriam ainda mais.

## O que este experimento NÃO mostra

- Comportamento em N > 20.
- Sintaxe compacta — só verbosa.
- Otimização da heurística (ana.lima escapou).
- Re-Pair recursivo (símbolos contendo refs a outros símbolos).
- Comparação com formato compacto, CSV, JSON, HTFC.
- Custo computacional do Re-Pair em escala.
- Casos onde Patricia bidirecional venceria Re-Pair (se houver).

## Recomendações para próximos passos

O exp 13 sugere repensar o caminho dos exps 02-12:

1. **Re-Pair domina nos cenários testados**. Os exps 02-12
   construíram Patricia bidirecional + composição com complexidade
   crescente. Re-Pair faz tudo numa única passada, com algoritmo
   mais simples.

2. **Continuação imediata**:
   - **exp 14**: revisar marcadores caros — sintaxe compacta sobre
     o output do Re-Pair. Avaliar quanto ainda dá pra economizar.
   - **exp 15**: heurística de Re-Pair refinada (resolver o caso
     ana.lima, considerar ganho secundário de símbolos compartilhados).
   - **exp 16**: Re-Pair em dataset maior — D1 (20 linhas, padrão
     diferente) + dataset hipotético com 6+ recursos sob mesma
     base (validar D4-like em escala).

3. **Reavaliar exps 02-12 conforme sugerido**: como o user disse,
   "Depois podemos repensar os experimentos desde o 10 pra ter uma
   ideia do que fazer". O exp 13 mostra que a complexidade da
   composição forward+reverse pode não ser necessária se Re-Pair
   capturar o suficiente. Vale documentar os exps 10-12 como
   "exploração que motivou abandonar Patricia bidirecional em
   favor de Re-Pair".
