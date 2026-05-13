# Arvore PATRICIA — segmentacao incremental linha a linha

**Data**: 2026-05-17
**Origem**: insight do user — em vez de inserir char-by-char, ir
fragmentando nos baseado em LCP entre LINHAS inteiras.

## O que eh PATRICIA trie (Practical Algorithm To Retrieve Information
Coded In Alphanumeric)

Trie onde cada no tem um **rotulo string** (nao 1 char). Quando o
caminho nao se ramifica, varios chars ficam num so no. Resultado:
arvore com poucos nos profundos em vez de muitos nos rasos.

Para nosso caso (compressao de strings columnares):
- Cada string da coluna eh inserida na trie
- Inserir uma string nova **fragmenta** nos existentes quando ha LCP
  parcial
- Resultado: arvore onde cada caminho da raiz a folha eh uma string
  da coluna

## Algoritmo de insercao

```
def insert(node, value, line_idx):
    # Acha filho onde value comeca com mesmo char
    for child in node.children:
        if value[0] == child.label[0]:
            lcp = compute_lcp(child.label, value)

            if lcp == len(child.label):
                # value tem prefix completo do child label
                # Recurse no resto
                insert(child, value[lcp:], line_idx)
                return

            # Split: child precisa virar dois nos
            common = child.label[:lcp]
            old_rest = child.label[lcp:]
            new_rest = value[lcp:]

            # Cria no intermediario com `common`
            # Antigo `child` perde `common` do label
            # Novo no com new_rest entra como sibling

            new_intermediate = Node(label=common)
            child.label = old_rest  # encurta
            new_intermediate.children = [child]
            new_intermediate.children.append(Node(label=new_rest, lines=[line_idx]))

            # Substitui child por new_intermediate na lista de filhos
            ...
            return

    # Nenhum filho casou — adiciona como novo
    node.children.append(Node(label=value, lines=[line_idx]))
```

## Exemplo do user (4 emails)

```
1: user019@yahoo.com
2: user014@gmail.com
3: user010@gmail.com
4: user026@yahoo.com
```

**Apos inserir linha 1**:
```
root
└── "user019@yahoo.com" [line=1]
```

**Apos inserir linha 2** (LCP com linha 1 = "user01"):
```
root
└── "user01"
    ├── "9@yahoo.com" [line=1]
    └── "4@gmail.com" [line=2]
```

**Apos inserir linha 3** (LCP com "4@gmail.com" = ""; LCP com "9@yahoo.com" = ""; mas com root child "user01" = "user01" exato):
```
root
└── "user01"
    ├── "9@yahoo.com" [line=1]
    ├── "4@gmail.com" [line=2]
    └── "0@gmail.com" [line=3]
```

**Apos inserir linha 4** (LCP com "user01" = "user0"):
```
root
└── "user0"
    ├── "1"
    │   ├── "9@yahoo.com" [line=1]
    │   ├── "4@gmail.com" [line=2]
    │   └── "0@gmail.com" [line=3]
    └── "26@yahoo.com" [line=4]
```

## Otimizacao adicional — sufixo comum

Apos construir a arvore, um pass de **suffix-merge** pode detectar
que `@yahoo.com`, `@gmail.com` aparecem no fim e merge-las:

```
root
└── "user0"
    ├── "1"
    │   ├── "9" → SUFFIX_A (@yahoo.com)
    │   ├── "4" → SUFFIX_B (@gmail.com)
    │   └── "0" → SUFFIX_B (@gmail.com)
    └── "26" → SUFFIX_A (@yahoo.com)

SUFFIX_A = "@yahoo.com"
SUFFIX_B = "@gmail.com"
```

Sufixos viram **idx separados**. Linha = caminho da raiz a folha +
sufixo idx.

## Serializacao

Apos construir + otimizar, percorre arvore por DFS (ordem das linhas
originais) e emite tokens por linha.

Sintaxe proposta:
- Cada no interno com count >= 2 ganha um **idx** (1-based pela ordem
  de DFS)
- Cada linha eh `<idx1> <idx2> ... <suffix-literal-ou-idx>`

Para o exemplo:
- root → "user0" (idx 1, count=4)
- "user0" → "1" (idx 2, count=3)
- "1" tem 3 filhos folha, cada um eh literal
- SUFFIX_A = "@yahoo.com" (idx 3, count=2)
- SUFFIX_B = "@gmail.com" (idx 4, count=2)

Emit:
```
linha 1 (user019@yahoo.com): 1 2 9 3   ← user0+1+9+@yahoo.com
linha 2 (user014@gmail.com): 1 2 4 4   ← user0+1+4+@gmail.com
linha 3 (user010@gmail.com): 1 2 0 4   ← user0+1+0+@gmail.com
linha 4 (user026@yahoo.com): 1 26 3    ← user0+26+@yahoo.com
```

Mas `26` eh literal (so 1 ocorrencia). Ambiguidade com idx 26 (que
nao existe). Decoder precisa saber que so existem idx 1-4. Se >4,
eh literal numero. Hmm, fragil.

**Solucao melhor**: marcadores nos tokens.
- `*<text>` decl
- `<idx>` ref
- `_<num>` literal numerico
- `<text>` literal

## Observacoes

1. **A arvore eh autoexplicativa** — caminho raiz→folha = string
2. **Nos internos com count alto** = candidatos a idx
3. **RLE-de-linha emerge** quando duas folhas tem mesma linha (mas
   nao eh comum em PATRICIA standard)
4. **Multi-modo natural**: cada folha pode usar suffix-idx
   independentemente, modo se adapta linha a linha

## Algoritmo proposto (simplificado para o lab)

1. **Pass 1** (constroi): inserir cada string em PATRICIA trie
2. **Pass 2** (otimiza): detectar suffixes comuns; mover para idx
3. **Pass 3** (numera): atribuir idx a nos internos com count >= 2
4. **Pass 4** (emit): para cada string, walk da raiz, emit tokens

## Cenarios para teste

| # | Dataset | Esperado |
|---|---------|----------|
| C1 | 4 emails do exemplo do user | arvore visualizada bate com manual |
| C2 | 30 emails 2 dominios | suffix-merge ativa |
| C3 | 20 codigos PED-2026-NNNN | trie linear; so 1 idx (prefix) |
| C4 | Misto sem padrao | arvore esparsa |

## Saida

`./output/<C>/`:
- `literal.txt`
- `tree.txt` — arvore visualizada (text-art)
- `encoded.txt` — emit final
- `bytes.json`

---

## Resultados

### Arvore visualizada — C1 (4 emails do user)

```
root
└── 'user0'
    ├── '1'
    │   ├── '9@yahoo.com' [lines=[1]]
    │   ├── '4@gmail.com' [lines=[2]]
    │   └── '0@gmail.com' [lines=[3]]
    └── '26@yahoo.com' [lines=[4]]
```

**Bate exatamente com a inducao manual proposta pelo user**.
Confirma que algoritmo PATRICIA fragmenta corretamente.

### Arvore visualizada — C3 (codigos PED)

```
root
└── 'PED-2026-00'
    ├── '0'
    │   ├── '1' [lines=[1]]
    │   ├── '2' [lines=[2]]
    │   ...
    ├── '1'
    │   ├── '0' [lines=[10]]
    │   ...
```

PATRICIA captura `PED-2026-00` como prefix dominante; depois ramifica
por `00..09`, `10..19`, etc. Estrutura hierarquica natural.

### Tabela bytes

| Cenario | literal | encoded | vs lit | RT |
|---------|--------:|--------:|-------:|----|
| C1 user-4-emails | 72 | 87 | +20.8% | OK |
| C4 user-full | 149 | 131 | -12.1% | OK |
| C2 emails-2dom | 540 | 462 | -14.4% | OK |
| **C3 codigos-uniforme** | 280 | **171** | **-38.9%** | OK |
| **medias** | | | **-11.2%** | **4/4 OK** |

### Comparativo com lab anterior

| Lab | Tecnica | Avg vs literal |
|-----|---------|---------------:|
| 2026-05-16 multi-index inline | inline decls | **-21.0%** |
| 2026-05-17 PATRICIA + header | header decls | -11.2% |

**Lab anterior (inline) economiza mais bytes**. PATRICIA com header
separado eh **mais verboso** mas estruturalmente mais claro.

### Insight critico

A **arvore PATRICIA** eh excelente para:
1. **Visualizacao** — mostra hierarquia natural
2. **Analise** — identifica nos uteis (count >= 2)
3. **Pre-computacao** de pass 2 (sabe todos prefixes globalmente)

Mas a **serializacao** compacta deveria usar **declaracoes inline**
(como no lab 16), nao header explicito. A arvore eh **guia**, nao
**template literal**.

### Por que C1 (micro) PIORA com PATRICIA

72B literal vs 87B encoded = +20.8%. Razao:
- Header com 5 decls: ~80B
- Body com 4 linhas: ~30B
- Total: 110B (mas saiu 87B com algumas otimizacoes)

Em datasets pequenos, decls de header **matam** o ganho. Em
datasets >= 20 valores, comeca a vencer (C2: -14.4%; C3: -38.9%).

### Refinamento implementado durante o lab

Bug detectado: encoder declarava **todos os prefixes candidatos**
(count >= 2), incluindo ancestrais que nenhuma string usava. Fix:
**filtrar so os usados** apos pass de selecao. Resultado: C2 melhorou
de -12.6% para -14.4%.

### Conexao com a literatura

PATRICIA trie eh tecnica classica:
- Morrison 1968 (PATRICIA original)
- Knuth TAOCP vol 3 (Section 6.3)
- Algoritmo padrao de compressao de chaves em B+trees

Nossa contribuicao: **construcao incremental linha-a-linha** com
visualizacao, em formato textual (ASCII puro).

### Limitacoes registradas

| # | Limitacao | Solucao proposta |
|---|-----------|------------------|
| L1 | Header verboso vs inline | Combinar PATRICIA (analise) + serializacao inline (lab 16) |
| L2 | Suffix-merge eh post-hoc, nao construido na arvore | Bidir-PATRICIA (mais complexo) |
| L3 | Decls duplicadas quando hierarquia profunda | Encadeamento (`*p2=p1+ext`) |
| L4 | Visualizacao so funciona ate ~30 nos | Truncate ou usar graphviz |

### Decisao para proxima iteracao

A **arvore PATRICIA validou o conceito** de segmentacao incremental.
Para producao, **combinar**:
- PATRICIA para **analise** (descobrir hierarquia)
- Serializacao **inline** (lab 16) para **emit compacto**
- Suffix-merge como **pass 2**

A separacao "analise vs emit" eh chave: arvore informa decisoes,
mas saida final usa formato denso.

### Status

- [x] PATRICIA trie incremental implementado
- [x] Visualizacao text-art da arvore
- [x] Bate manualmente com inducao do user (C1 = 4 emails)
- [x] 4/4 RT OK
- [x] Bug de selecao de prefixes corrigido durante lab
- [x] Conexao com literatura (PATRICIA = Morrison 1968)
- [ ] (futuro) Combinar com serializacao inline do lab 16
- [ ] (futuro) Bidir-PATRICIA capturando suffixes na construcao
- [ ] (futuro) Encadeamento `*p2=p1+ext` para hierarquias profundas
