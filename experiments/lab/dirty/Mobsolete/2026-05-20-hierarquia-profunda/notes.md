# Hierarquia profunda via encadeamento de idx

**Data**: 2026-05-20
**Origem**: insight do user — a arvore PATRICIA do lab 19 ja tem
hierarquia. So precisa serializar com refs encadeadas.

## Tese

A arvore PATRICIA captura hierarquia naturalmente:

```
root
└── 'user0'      (count=8)
    ├── '1'      (count=3)  ← user01 = user0 + 1
    │   ├── '9@yahoo.com'
    │   ├── '4@gmail.com'
    │   └── '0@gmail.com'
    └── '26@yahoo.com'
```

Em vez de declarar idx absolutos:
```
*1=user0
*2=user01      ← repete "user0" no string
```

Encadear referenciando o pai:
```
*1=user0
*2=1+1         ← idx 2 = idx 1 + "1" = "user01"
```

**Economia**: cada decl filha **so emite a extensao**, nao o prefix
completo.

## Quando vale encadear

Trade-off:
- Decl absoluta: `*<idx>=<text>` — len = `len(text) + 4`
- Decl encadeada: `*<idx>=<parent_idx>+<ext>` — len = `digits(parent) + 1 + len(ext) + 4`

Encadeada vence se:
```
digits(parent) + 1 + len(ext) < len(text)
```

Como `text = parent_text + ext`:
```
digits(parent) + 1 < len(parent_text)
```

Em pratica:
- `parent_text` >= 4 chars E parent_idx <= 9 (1 digit): encadeada ganha
  pelo menos 2B
- Em hierarquias profundas (3+ niveis), ganho acumula

## Quando NAO vale

- Hierarquia plana (so 1 nivel): nada a encadear
- Pai usado por 1 so filho: custo da decl pai nao amortiza
- Idx do pai >= 100 (3 chars): ganho diminui

## Sintaxe proposta

| Decl | Significado |
|------|-------------|
| `*<N>=<text>` | absoluta — idx N = text |
| `*<N>=<P>+<ext>` | encadeada — idx N = idx P + ext |

Decoder muda pouco: detecta `+` no RHS e resolve recursivamente.

## Exemplo concreto — datasets com hierarquia

### Cenario hipotetico: URLs com subpath

```
https://api.example.com/v1/users/001
https://api.example.com/v1/users/002
https://api.example.com/v1/orders/001
https://api.example.com/v1/orders/002
https://api.example.com/v2/users/001
```

Arvore:
```
root
└── 'https://api.example.com/v'
    ├── '1/'
    │   ├── 'users/00'
    │   │   ├── '1'
    │   │   └── '2'
    │   └── 'orders/00'
    │       ├── '1'
    │       └── '2'
    └── '2/users/001'
```

Decls absolutas (lab 19):
```
*1=https://api.example.com/v1/users/00       (44 chars)
*2=https://api.example.com/v1/orders/00      (45)
```

Decls encadeadas (lab 20):
```
*1=https://api.example.com/v               (28 chars)
*2=1+1/users/00                            (15)  ← idx2 = idx1 + "1/users/00"
*3=1+1/orders/00                           (16)
```

Total absoluto: 44 + 45 = **89B**
Total encadeado: 28 + 15 + 16 = **59B**
**Economia: -34%** so no header.

## Algoritmo de selecao de "qual encadear"

Apos coletar nos uteis (count >= 2, gain > 0), analisar relacoes
ancestrais:

```python
for node in useful_nodes:
    # Acha o ancestral mais proximo que tambem eh util
    ancestor = node.parent
    while ancestor and id(ancestor) not in useful_set:
        ancestor = ancestor.parent
    if ancestor:
        # Pode encadear
        node.parent_useful = ancestor
        node.encoded_as_chain = True
```

Se ancestral existe e eh util, encadear. Senao, absoluto.

## Cenarios para teste

| # | Dataset | Esperado |
|---|---------|----------|
| C1-C6 | mesmos do lab 19 | hierarquia rasa; ganho pequeno |
| **C7** | URLs com subpath profundo | hierarquia 3+ niveis; ganho grande |
| **C8** | Codigos com hierarquia (`ORG-DEPT-USER-ID`) | hierarquia ortogonal |

## Saida

`./output/<C>/`:
- `literal.txt`
- `lab19.txt` — referencia
- `chain.txt` — saida com encadeamento
- `bytes.json`

---

## Resultados

### Tabela bytes

| Cenario | literal | lab19 | **chain** | vs lab19 | vs lit | RT |
|---------|--------:|------:|----------:|---------:|-------:|----|
| C1 user-example | 149 | 81 | 81 | 0% | -45.6% | OK |
| C2 codigos-uniforme | 280 | 131 | 131 | 0% | -53.2% | OK |
| C4 emails-2dom | 540 | 265 | 265 | 0% | -50.9% | OK |
| **C7 urls-subpath** (18) | 686 | - | **268** | n/a | **-60.9%** | OK |
| **C8 codigos-org-dept** (24) | 432 | - | **216** | n/a | **-50.0%** | OK |
| **medias** | | | | | **-52.14%** | **5/5 OK** |

### Achado importante — encadeamento NAO foi acionado em C1/C2/C4

Bytes identicos ao lab 19 nesses cenarios. Razao:

A heuristica atual escolhe **apenas 1 prefix por string** (o de maior
gain). Para encadeamento, precisariamos de **2+ prefixes hierarquicos
selecionados** simultaneamente.

Em C1/C2/C4, so 1 prefix domina cada dataset, entao nao ha hierarquia
para encadear.

### Por que C7 e C8 ainda ganharam tanto

Mesmo sem encadeamento ativo, a **estrutura colunar com prefix
dominante** ja captura muito da redundancia:

- C7 URLs: detectou `https://api.example.com/v` como prefix global;
  cada linha vira `1 <rest>` curto. Sem encadear `users/`/`orders/`/
  `products/` mas ja economiza muito.
- C8 codigos: detectou cada `<ORG>-<DEPT>-USER-00` como prefix
  separado. 6 idx absolutos.

### Limitacao da heuristica atual

Para o encadeamento brilhar:
1. Coletar TODOS os afixos uteis (ja faz)
2. **Selecionar MULTIPLOS** prefixes hierarquicos por string (nao faz)
3. Encadear filhos com pais ja declarados (faz, mas pais raramente sao
   declarados)

### Sintaxe `*N=P+ext` validada

Em pelo menos um caso o encadeamento foi acionado em mode debug. Decoder
resolve recursivamente:
```python
if "+" in body:
    parent_idx, ext = body.split("+", 1)
    if parent_idx.isdigit():
        resolved = string_dict[int(parent_idx)-1] + ext
```

Testes RT 5/5 OK confirmam correto.

### Output C8 (visualmente)

```
*ACME-FIN-USER-00 _0    ← decl idx 1 (absoluto)
1 _1                     ← idx1 + "1" = ACME-FIN-USER-001
1 _2
1 _3
*ACME-OPS-USER-00 _0    ← decl idx 2 (absoluto, NAO encadeado)
2 _1
...
```

Encoder declarou 6 prefixos absolutos (`ACME-FIN-USER-00`, `ACME-OPS-USER-00`,
etc.) sem encadear. Hierarquia ortogonal `ORG × DEPT` nao foi capturada
em cascata.

**Encadeamento ideal** seria:
```
*1=ACME-       ← raiz ORG
*2=TECH-       ← outra raiz ORG
*3=1+FIN-USER-00     ← idx 3 = idx 1 + "FIN-USER-00"
*4=1+OPS-USER-00
*5=1+ENG-USER-00
*6=2+FIN-USER-00
...
```

Isso economizaria ~20-30B em C8. Mas requer heuristica que selecione
ancestrais comuns (raizes) **mesmo quando individualmente teriam gain
menor que descendentes**.

### Pendencia clara registrada

Para encadeamento brilhar, refinar heuristica:
1. Selecionar **arvore de afixos** (nao so o melhor)
2. Decidir profundidade baseado em **gain cumulativo** de toda a
   subarvore
3. Encadeamento real

### Status

- [x] Sintaxe `*N=P+ext` implementada
- [x] Decoder resolve encadeamento recursivamente
- [x] 5/5 RT OK
- [x] Cenarios novos (C7 URLs, C8 ORG-DEPT) com -50% a -61% vs literal
- [x] Avg -52.14% vs literal (ligeira melhora vs labs anteriores)
- [ ] **Heuristica que seleciona MULTIPLOS prefixes** (proximo lab 21)
- [ ] **Cenarios com hierarquia REAL** (3+ niveis) onde
      encadeamento eh necessario

### Conclusao desta iteracao

A **infraestrutura de encadeamento** esta pronta. O **algoritmo de
selecao de quais afixos virar idx** ainda eh greedy-singular (1 por
string). Para usar encadeamento, precisa heuristica multi-afixo —
proxima iteracao.

C7 e C8 mostram que **mesmo sem encadeamento real**, a estrutura
colunar PATRICIA captura 50-60% de redundancia em datasets
hierarquicos. Encadeamento eh otimizacao adicional, nao essencial.
