# Algoritmo — Patricia v0.6 (refeito)

Refeito do zero. Não importa nada de `dirty/old/2026-05-17-arvore-patricia/`
nem dos labs subsequentes. Estrutura e nomes de função são novos.

## Estrutura de dado

```python
@dataclass
class No:
    id: int                       # estavel desde fase 1
    pai_id: Optional[int]         # None se top-level
    fragmento: str                # se top-level: string completa
                                  # senao: sufixo a partir do pai
```

Reconstrução do texto completo de um nó:

```python
def texto_completo(no_id, nos):
    n = nos[no_id]
    if n.pai_id is None:
        return n.fragmento
    return texto_completo(n.pai_id, nos) + n.fragmento
```

## Três fases

### Fase 1 — `construir_inicial(linhas) -> (nos, body)`

Cada **valor único** vira folha top-level com id sequencial.
Body é a sequência de `no_id` por linha do CSV.

Para `[Ana, Ana, Bob, Ana]`:

```
nos = {1: No(1, None, "Ana"), 2: No(2, None, "Bob")}
body = [1, 1, 2, 1]
```

### Fase 2 — `aplicar_patricia(nos)`

Iterativo. Em cada passada:

1. Lista todos os nós **top-level**.
2. Conta prefixos próprios (`v[:k]` com `MIN_PREFIXO ≤ k < len(v)`)
   de cada nó top-level.
3. Filtra prefixos com contagem ≥ `MIN_GRUPO`.
4. Pega o **mais longo** (desempate por mais frequente, depois lex).
5. Cria nó pai novo top-level com `fragmento = prefixo`.
6. Para cada folha que começa com o prefixo, atualiza:
   `pai_id = id_do_pai_novo`, `fragmento = sufixo`.
7. Repete até não haver mais candidatos.

O **id do nó folha não muda**. Somente seu `pai_id` e `fragmento`.
Refs antigas no body continuam válidas.

Em B com `[USR0001..USR0010, PRD0001..PRD0005]`:

```
Iteração 1:
  prefixos top-level com ≥ 2: "U"(10), "USR"(10), "USR000"(10),
                              "P"(5), "PRD"(5), "PRD000"(5), ...
  mais longo: "USR000" (len 6, count 10)
  cria no18 = "USR000"; USR0001..USR0009 viram filhos com sufixo "1".."9"
  USR0010 NÃO entra (não começa com "USR000" — começa com "USR001")
  Ah não, "USR0010" começa com "USR000" sim. Reler abaixo.
```

**Detalhe importante**: na execução real, a primeira iteração
escolheu `"USR00"` (não `"USR000"`) porque `USR0010` também conta para
prefixo `"USR00"` (10 ocorrências) mas não para `"USR000"` (só 9 — pois
`USR0010` começa com `"USR001"`, não `"USR000"`). Como ambos têm
count diferente, e o algoritmo prefere mais longo, escolheu o que tem
maior **len** com count `≥ 2`. Verificar:

- `"USR00"`: prefixo de USR0001..USR0010 — count 10
- `"USR000"`: prefixo de USR0001..USR0009 — count 9
- `"USR0010"`: count 1 — fora

Mais longo + count ≥ 2: `"USR000"` (len 6, count 9). Mas
`"USR00"` (len 5, count 10) tem count maior. Como o desempate é
**primeiro por len, depois por count**, `"USR000"` venceria.

Mas a árvore real tem `USR00` no top, com `USR000` como filho. Por
quê? Porque numa segunda iteração, depois que `USR0001..USR0009` foram
absorvidos pelo nó pai escolhido na iteração 1, restou `USR0010` ainda
top-level. Para casar `USR0010` em alguma estrutura comum com os
demais foi necessário um pai mais raso.

Inspecionando a saída real: top é `USR00` (`no18`), e `USR000` é
filho dele (`no16`), com `USR0001..USR0009` como netos. `USR0010`
está direto em `USR00` com sufixo `"10"`. Então o algoritmo na
iteração 1 escolheu `"USR00"` (não `"USR000"`). A regra de desempate
implementada está em [patricia.py](patricia.py):

```python
candidatos.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))
```

Mais longo primeiro. Por que `USR00` venceu `USR000`? Porque o ranger
do prefixo é `range(MIN_PREFIXO, len(v))` — **prefixo próprio**. Para
`USR0001` (len 7), gera `USR`(3), `USR0`(4), `USR00`(5), `USR000`(6).
Para `USR0010`, gera `USR`(3), `USR0`(4), `USR00`(5), `USR001`(6).

- `USR00` (len 5): count 10 (todos USR têm)
- `USR000` (len 6): count 9 (não USR0010)
- `USR001` (len 6): count 1

Mais longo dos com count ≥ 2: ambos `USR000` (6) e `USR001` (6) têm
len 6, mas `USR001` tem count 1. Só `USR000` qualifica em len 6 →
escolhido. Espere, então `USR000` venceria `USR00`. Por que a árvore
mostra `USR00` no topo?

Pista: depois que `USR000` foi escolhido na iteração 1 e criou pai
para USR0001..USR0009, sobra `USR0010` top-level. Iteração 2:
top-levels são `USR0010`, `USR000`(o nó pai), `PRD0001..PRD0005`.
Prefixos comuns:

- `USR000` ↔ `USR0010`: prefixo comum `"USR00"` (len 5).
- `PRD0001..PRD0005`: prefixos próprios `"PRD"`(3), `"PRD0"`(4),
  `"PRD00"`(5), `"PRD000"`(6).

Mais longo com count ≥ 2: `"PRD000"` (len 6, count 5). É escolhido.
Cria `no17 = "PRD000"`, fatora `PRD0001..PRD0005`.

Iteração 3: top-levels `USR000`, `USR0010`, `PRD000`. Prefixo comum
entre `USR000` e `USR0010` é `"USR00"` (len 5, count 2). `PRD000`
sozinho. Escolhido `"USR00"` → cria pai `no18`, ambos `USR000` e
`USR0010` viram filhos.

Iteração 4: top-levels `USR00` e `PRD000`. Sem prefixo comum ≥ 3 →
para.

Estado final consistente com a saída real:

```
no17 = "PRD000"   (top, criado iter 2)
  no3, no5, no9, no12, no15 = filhos com sufixos "1".."5"
no18 = "USR00"   (top, criado iter 3)
  no14 = filho com sufixo "10"  (USR0010)
  no16 = "USR000"   (filho, era top em iter 1, virou filho em iter 3)
    no1..no13 (varios) = netos com sufixos "1".."9"
```

Ou seja, o algoritmo é **online incremental**: cada iteração escolhe
o melhor prefixo do estado atual, e a estrutura emerge. **Não é a
árvore Patricia ótima global**; é uma aproximação gulosa.

### Fase 3 — `rle_adjacente(body) -> [(no_id, rep)]`

Comprime runs de mesmo `no_id` adjacentes. Linear, single-pass.

```
[1, 1, 2, 1, 2, 2] -> [(1, 2), (2, 1), (1, 1), (2, 2)]
```

## Decisão: RLE no body, não no nó

O exemplo do user descrevia `no1 = 2x Ana`. Isso colocaria RLE como
propriedade do nó, mas misturaria duas coisas distintas:

- **Nó** = declaração de uma string única + relação Patricia.
- **Body** = sequência de ocorrências em cada linha.

Manter separado simplifica decode (parser linear) e permite que a
mesma string apareça em runs diferentes do body (`2x ref:no1`,
depois `3x ref:no1` mais à frente). Se RLE estivesse no nó, teria
que ser por-ocorrência, o que não é "no nó".

## Roundtrip

Decode é independente do encode. Parseia `<patricia>` e `<body>`
linha-a-linha via regex; reconstrói o texto completo de cada nó
recursivamente; expande RLE em ocorrências individuais. Compara com
o input do CSV linha-a-linha.

Verificado nos 2 cenários: `decoded == input` → OK.
