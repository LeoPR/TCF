# Conclusões — TCF aninhado em dados realistas

Roundtrip OK em **4/4 cenários**.

## D1 — emails com um domínio

Patricia construiu **árvore profunda** porque os emails compartilham
prefixos múltiplos (`user0`, `user00`):

```
no12 = "user0"
  no10 = pai(no12) + "10@gmail.com"       -> "user010@gmail.com"
  no11 = pai(no12) + "0"                  -> "user00"
    no1..no9 = pai(no11) + "N@gmail.com"  -> "user00N@gmail.com" (N=1..9)
```

Observe que `user010@gmail.com` cai diretamente em `user0` (pai mais
raso) com sufixo `"10@gmail.com"`, **não** em `user00` (que tem
sufixo `"0"`). Patricia não "vê" semanticamente que 010 é a
continuação de 001-009; trata como apenas mais uma string com
prefixo parcial.

TCF (extrato):

```
no1: filho_de(no2=decl filho_de(no3=decl folha "user0") + "0") + "1@gmail.com"
no4: filho_de(no2) + "2@gmail.com"
ref:no1
no5: filho_de(no2) + "3@gmail.com"
...
no12: filho_de(no3) + "10@gmail.com"
ref:no7
ref:no1
```

Leitura da linha 1:
- `no1` é declarado para `user001@gmail.com`.
- Dentro dela, `no2` é declarado para `user00` (pai imediato).
- Dentro de no2, `no3` é declarado para `user0` (avô top-level).
- Cadeia de 3 níveis aninhada na primeira linha do body.

Linha por linha:
- Linhas seguintes (no4 = user002, no5 = user003, ...) só precisam
  de `filho_de(no2)` — `user00` já declarado.
- Linha de `user010@gmail.com` (`no12`) usa `filho_de(no3)` direto
  porque seu pai é o avô (no3 = "user0"), não `user00`.

### Sufixo `@gmail.com` não foi fatorado

Patricia só fatora prefixos. `@gmail.com` aparece em 10 folhas
diferentes, mas o algoritmo não o detecta como **sufixo comum**.
Cada folha carrega `@gmail.com` no seu fragmento individual.

## D2 — emails com múltiplos domínios

Patricia identificou **4 prefixos paralelos** (um por nome de
pessoa), cada um com 3 filhos (um por domínio):

```
no13 = "maria.silva@"
  no1, no3, no10 = + "gmail.com", "hotmail.com", "yahoo.com"
no14 = "pedro.alves@"
  no6, no9, no12 = + "yahoo.com", "gmail.com", "hotmail.com"
no15 = "joao.souza@"
  no2, no5, no8 = + "hotmail.com", "gmail.com", "yahoo.com"
no16 = "ana.lima@"
  no4, no7, no11 = + "gmail.com", "hotmail.com", "yahoo.com"
```

TCF (extrato):

```
no1: filho_de(no2=decl folha "maria.silva@") + "gmail.com"
no3: filho_de(no4=decl folha "joao.souza@") + "hotmail.com"
no5: filho_de(no2) + "hotmail.com"
no6: filho_de(no7=decl folha "ana.lima@") + "gmail.com"
no8: filho_de(no4) + "gmail.com"
no9: filho_de(no10=decl folha "pedro.alves@") + "yahoo.com"
...
```

Cada um dos 4 prefixos foi declarado **na 1ª ocorrência da pessoa
correspondente**:
- Linha 1: `maria.silva@` (no2) embutido em `maria.silva@gmail.com`
- Linha 2: `joao.souza@` (no4) embutido em `joao.souza@hotmail.com`
- Linha 4: `ana.lima@` (no7) embutido em `ana.lima@gmail.com`
- Linha 6: `pedro.alves@` (no10) embutido em `pedro.alves@yahoo.com`

Sem cadeias profundas — não há prefixo comum entre os 4 nomes,
então cada um vira top-level independente.

### Domínios `gmail.com`, `hotmail.com`, `yahoo.com` não foram
agrupados

Mesma observação do D1: são sufixos compartilhados, e Patricia atual
não fatora sufixos.

## D3 — URLs com path comum

Patricia identificou **1 prefixo grande** (33 chars):

```
no11 = "https://api.example.com/v1/users/"
  no1..no10 = + "1", "2", ..., "10"
```

TCF:

```
no1: filho_de(no2=decl folha "https://api.example.com/v1/users/") + "1"
no3: filho_de(no2) + "2"
ref:no1
no4: filho_de(no2) + "3"
ref:no3
no5: filho_de(no2) + "4"
...
no10: filho_de(no2) + "9"
ref:no5
no11: filho_de(no2) + "10"
ref:no6
ref:no1
```

Padrão limpo: 1 linha embute o pai grande (`no2`, 33 chars), todas
as demais 9 declarações de IDs só usam `filho_de(no2)`. O sufixo
de cada folha é só o número (`"1"`, `"2"`, ..., `"10"`).

Cenário canônico para Patricia: prefixo dominante + sufixos
mínimos.

## D4 — URLs multi-recurso (3 níveis Patricia)

Patricia identificou **avô + 3 filhos intermediários + folhas**:

```
no16 = "https://api.example.com/v1/"
  no13 = pai(no16) + "products/5"
    no5, no7, no11 = + "0", "1", "2"     -> products/50, /51, /52
  no14 = pai(no16) + "orders/10"
    no2, no4, no8, no9, no12 = + "0", "1", "2", "3", "4"
  no15 = pai(no16) + "users/"
    no1, no3, no6, no10 = + "1", "2", "3", "4"
```

**3 níveis Patricia**: base, recurso, ID. Observação interessante:
Patricia agrupou `orders/10` e `products/5` como nós internos
porque os IDs compartilhavam prefixo numérico (10X para orders,
5N para products). `users/` ficou como nó intermediário sem
agrupamento de prefixo numérico (porque os IDs `1..4` não
compartilham prefixo significativo).

TCF (extrato):

```
no1: filho_de(no2=decl filho_de(no3=decl folha "https://api.example.com/v1/") + "users/") + "1"
no4: filho_de(no5=decl filho_de(no3) + "orders/10") + "0"
no6: filho_de(no2) + "2"
no7: filho_de(no5) + "1"
no8: filho_de(no9=decl filho_de(no3) + "products/5") + "0"
ref:no1
ref:no4
...
```

Leitura:
- **Linha 1** (`https://api.example.com/v1/users/1`): cadeia de 3
  níveis na mesma linha. Declara `no3` (avô,
  `https://api.example.com/v1/`), `no2` (pai, `users/`), `no1`
  (folha, `1`).
- **Linha 2** (`https://api.example.com/v1/orders/100`): reaproveita
  `no3` (já declarado), declara `no5` (novo pai,
  `https://api.example.com/v1/orders/10`), e `no4` (folha, `0`).
- **Linha 5** (`https://api.example.com/v1/products/50`): reaproveita
  `no3` novamente, declara `no9` (`https://api.example.com/v1/products/5`),
  `no8` (folha, `0`).

**Reaproveitamento do avô em ramos paralelos** funciona como
esperado. O avô `no3` é declarado uma única vez (na linha 1) e
serve de raiz para os 3 nós intermediários (`no2`, `no5`, `no9`),
cada um declarado na 1ª ocorrência do seu ramo.

## Pontos a registrar

1. **Roundtrip 4/4 OK**. Mesmo encoder/decoder do 05 funciona em
   dados realistas sem modificação.

2. **Cadeia de 3 níveis aninhada** acionou em D1 (linha 1) e D4
   (linha 1). Profundidade real da árvore se reflete diretamente
   na profundidade do aninhamento na 1ª linha que precisa de cada
   pai.

3. **Reaproveitamento de avô** em D4: `no3` (base URL) declarado
   uma vez, usado como raiz por 3 nós intermediários diferentes
   nas linhas subsequentes. Sem duplicação.

4. **Patricia não fatora sufixos**. Em D1 (`@gmail.com` em 10
   folhas) e D2 (3 domínios em todas as 4 famílias), o sufixo
   comum permanece duplicado em cada folha. Sufixo-DICT seria
   outra ferramenta — não testada aqui.

5. **D4 mostra hierarquia natural**: base + recurso + ID. Patricia
   reconstrói essa estrutura automaticamente quando os dados a
   contêm. Ordem de declaração das 3 famílias (users → orders →
   products) segue a ordem de 1ª aparição no body.

## O que este experimento NÃO mostra

- Comportamento em N grande (20 linhas por cenário).
- URLs com query strings, fragmentos, ports, schemes mistos
  (http vs https), encoding URL.
- Emails com tags (`user+promo@gmail.com`), pontos no local-part
  (`john.doe`), case mix.
- Distribuição realista (Pareto) de domínios e de IDs.
- Comparação numérica com formato compacto, CSV ou JSON.
- Sufixo-DICT (não está no escopo da Patricia atual).
- Otimização da numeração de eids — `no1, no2, ...` ainda é ordem
  de aparição, herdada do exp 05.
