# Trie de prefixos compartilhados — versao avancada do affix

**Data**: 2026-05-12
**Origem**: proposta do user apos analise do EXP affix-bidir

## Conceito

Ao inves de **um** prefix dominante, construir uma **arvore (trie)** onde
cada no representa um prefix candidato. Cada string aponta para o no
mais profundo que ainda eh comum a multiplas strings.

### Exemplo do user (7 emails)

```
user057@gmail.com
user026@outlook.com
user005@outlook.com
user013@yahoo.com
user061@yahoo.com
user024@gmail.com
user022@yahoo.com
```

Arvore inferida:

```
"" (root)
└── user (count=7)
    └── user0 (count=7)
        ├── user05 (count=2)  → user057, user005
        ├── user02 (count=2)  → user026, user024, user022 (wait, 3...)
        └── user0X (varios)
```

Nos uteis (count >= 2):
- `user` (7)
- `user0` (7)
- `user02` (3)  ← user026, user024, user022
- `user05` (2)  ← user057, user005
- `user01` (1)  ← user013 (so 1, nao vale)
- `user06` (1)  ← user061 (so 1, nao vale)

Selecao (mais profundo que vale):
- user057 → idx `user05`, sufixo `7@gmail.com`
- user026 → idx `user02`, sufixo `6@outlook.com`
- user005 → idx `user05`, sufixo `5@outlook.com`
- user013 → idx `user0`, sufixo `13@yahoo.com`
- user061 → idx `user0`, sufixo `61@yahoo.com`
- user024 → idx `user02`, sufixo `4@gmail.com`
- user022 → idx `user02`, sufixo `2@yahoo.com`

## Sintaxe proposta

```
email,t:                          # 't' = trie mode
*1=user0                          # declara prefix idx 1 = "user0"
*2=user02                         # declara idx 2 = "user02" (extensao de 1, mas a princ. todos absolutos)
*3=user05
1 13@yahoo.com                    # idx 1 + sufixo
1 61@yahoo.com
2 6@outlook.com
2 4@gmail.com
2 2@yahoo.com
3 7@gmail.com
3 5@outlook.com
```

Header: lista de prefixos numerados (linhas comecadas com `*`).
Body: linhas `<idx> <suffix>`.

### Variante 1 — header completo (acima)

Prefixos declarados como absolutos. Decoder le o header, monta dict
de prefix.

### Variante 2 — declaracao incremental (mais bytes economizados)

Cada prefix referencia o pai + extensao:

```
email,t:
*1=user0                          # absoluto
*2=1+2                            # idx 2 = idx 1 + "2" = "user02"
*3=1+5                            # idx 3 = idx 1 + "5" = "user05"
1 13@yahoo.com
...
```

Em prefixes longos com hierarquia, V2 economiza bytes (so emite a
extensao, nao o prefix completo).

### Variante 3 — inline progressivo (sintaxe original do user)

Cada linha do body pode declarar um novo prefix incrementalmente:

```
email,t:
us er057@gmail.com               # idx 1 = "us"
1 e r026@outlook.com             # idx 2 = idx 1 + "e" = "use"
2 r 005@outlook.com              # idx 3 = idx 2 + "r" = "user"
3 0 13@yahoo.com                 # idx 4 = idx 3 + "0" = "user0"
4 61@yahoo.com                   # ref idx 4 sem extensao
4 24@gmail.com
4 22@yahoo.com
```

Mais auto-documentavel. Mas decoder mais complexo (parse 3 partes).

## Implementacao no lab

Vou comecar com **Variante 1** (header completo) — mais simples de
implementar e validar conceito. Variante 2 e 3 ficam como possiveis
otimizacoes.

### Algoritmo

**Pass 1 — construir trie com TODAS as strings**

```python
class TrieNode:
    children: dict[str, TrieNode]
    count: int   # quantas strings passam por este no
    depth: int   # comprimento do prefix neste no

def build_trie(strings):
    root = TrieNode()
    for s in strings:
        node = root
        node.count += 1
        for c in s:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
            node.count += 1
            node.depth = node.parent.depth + 1
    return root
```

**Pass 2 — selecionar nos uteis**

Criterios para no virar idx:
1. count >= 2 (pelo menos 2 strings)
2. depth >= 4 (prefix nao trivial)
3. ganho previsto > overhead_decl

Ganho previsto: `count * (depth - len(idx_str) - 1) - len(declaration)`.

**Pass 3 — emitir**

Para cada string, achar nó marcado MAIS PROFUNDO. Emitir:
`<idx> <suffix>`

## Cenarios a testar

| # | Dataset | Esperado |
|---|---------|----------|
| E1 | 7 emails do exemplo do user | Validar visualmente |
| E2 | 100 emails 2 dominios (S3) | Trie deve detectar 2 sufixos |
| E3 | 100 emails 3 dominios (S4) | Trie deve detectar 3 sufixos |
| E4 | Codigos com 3 prefixos (S5) | Trie deve detectar 3 prefixos |

## Comparacao

Para cada cenario:
- CSV
- TCF SRDMP atual (etapa 1, prefix simples)
- TCF affix-bidir (lab anterior — cluster simples)
- **TCF trie** (este lab — multi-prefix com arvore)

Tudo com roundtrip OK requerido.

## Saida

`./output/<E>/`

---

## Resultados (apos otimizacao da arvore)

| Cenario | CSV | SRDMP | Trie | Trie vs SRDMP | Trie vs CSV | Prefs |
|---------|----:|------:|-----:|--------------:|------------:|------:|
| **E1** user example (7) | 136 | 150 | **134** | **-10.7%** | -1.5% | 2 |
| E2 emails 2 dominios (100) | 1806 | 1334 | 1520 | +13.9% | -15.8% | 10 |
| E3 emails 3 dominios (100) | 1872 | 1400 | 1586 | +13.3% | -15.3% | 10 |
| **E4** codigos 3 prefixes (100) | 1407 | 1421 | **975** | **-31.4%** | **-30.7%** | 30 |
| **medias** | | | | **-3.71%** | **-15.82%** | |

Roundtrip 4/4 OK.

## Analise critica

### Onde trie BRILHA (E1 e E4)

**E4 com -31.4%** eh o caso classico onde trie ganha de SRDMP simples.
3 familias distintas de prefixos (INV/PED/REQ) com sub-divisao
hierarquica. Trie detecta arvore e usa multiplos prefixes
especificos.

E1 (exemplo do user, 7 strings) tambem ganha pois detecta `user0` +
`user02` como sub-cluster.

### Onde trie PERDE (E2 e E3)

**E2/E3 +13-17% PIOR que SRDMP** apesar de detectar 10 prefixes.
Por que?

Cenario: 100 strings `userNNN@dominio` com NNN unicos. Trie detecta:
- `user0` (cobre todos 100)
- `user`, `user04`, `user09`, ..., `user02` (10 sub-clusters de 10
  strings cada)

Header com 10 declaracoes (~100B) eh maior que SRDMP que tem 1
declaracao (~20B). Body apenas marginalmente menor.

**Conclusao**: trie so ganha quando ha **HIERARQUIA real** (3+
familias claras com folhas). Em **estrutura plana** (1 prefix +
sufixo unico), SRDMP simples eh mais eficiente.

### Heuristica necessaria

Algoritmo deveria decidir entre 3 modos:

1. **No-prefix** (cardinalidade > N/2 ou LCP < 4) — sem affix
2. **SRDMP simples** (1 prefix dominante, count >= 70%) — flag P
3. **Trie multi-prefix** (estrutura hierarquica com 3+ ramos com
   count >= 5 cada e gain individual > overhead)

A escolha depende de **quantos** prefixes uteis emergem da analise:
- 1 prefix dominante → SRDMP
- 3+ prefixes com folhas distintas → trie
- caso intermediario → escolher por simulacao de bytes

### Roundtrip

OK em todos os 4 cenarios. Gramatica `email,t:` + `*N=prefix` +
body `idx suffix` esta sound.

## Decisao registrada

**Trie eh tecnica viavel mas nao universal.** Ganho real em E1
e E4. Prejuizo em E2/E3 onde estrutura eh plana.

Para implementar no core (futuro):
1. Detectar estrutura: contar candidatos com count >= threshold
2. Se 1 dominante (>= 70% cobertura): SRDMP simples (atual)
3. Se 3+ distintos (cada >= 10% cobertura): trie
4. Senao: no-affix

Auto-bypass em multiplos niveis.

### Sintaxe alternativa para considerar

Variante 3 (proposta original do user com declaracao incremental
inline) pode reduzir o overhead do header em casos com hierarquia
profunda (E4, 30 declaracoes), pois cada declaracao seria so 1-2
chars de extensao em vez do prefix completo.

Ex E4 (variante 3 hipotetica):
```
codigo,t:
INV-2026-0 003           # idx 1 = "INV-2026-0", sufixo "003"
1+0 0                    # idx 2 = idx 1 + "0" = "INV-2026-00", sufixo "0"
1+1 5                    # idx 3 = "INV-2026-01", sufixo "5"
PED-2026-0 001           # idx 4 = "PED-2026-0"
4+0 0
...
```

Em E4, com 30 prefixes mas a maioria sendo extensao do anterior, a
variante 3 economiza ~70% do header.

**Adiar** essa variante ate confirmacao de que vale a complexidade.

## Status

- [x] Trie de prefixos compartilhados (Variante 1) implementada
- [x] Otimizacao "so declarar usados"
- [x] Roundtrip 4/4 OK
- [x] Analise honesta: ganha em E1+E4, perde em E2+E3
- [ ] (futuro) Heuristica decidir SRDMP vs trie automaticamente
- [ ] (futuro) Variante 3 (declaracao incremental) se trie ganhar tracao
