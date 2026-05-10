# Lab 21: heuristica multi-afixo + encadeamento real

**Data**: 2026-05-21
**Origem**: lab 20 implementou sintaxe `*N=P+ext` mas heuristica
nao acionou. Aqui refina com pre-declaracao topologica.

## Algoritmo

1. PATRICIA forward + reverse
2. Para cada string, walk pela trie e identifica TODOS os nos uteis
   no caminho (nao so o melhor)
3. Pre-declara todos os nos usados em ordem topologica (raiz → folha)
4. Encadeia cada nivel com seu pai
5. Body emite caminho (idx do no mais profundo) + middle

## Resultados

| Cenario | literal | lab20 | **multi** | vs lab20 | vs lit | RT |
|---------|--------:|------:|----------:|---------:|-------:|----|
| C1 user-example | 149 | 81 | 123 | **+51.9%** | -17.4% | OK |
| **C7 urls-subpath** | 686 | 268 | **189** | **-29.5%** | **-72.4%** | OK |
| C8 codigos-org-dept | 432 | 216 | 240 | **+11.1%** | -44.4% | OK |
| **C9 urls-4-niveis** (novo) | 912 | - | **350** | n/a | **-61.6%** | OK |
| **medias** | | | | | **-48.99%** | **4/4 OK** |

### C9 — encadeamento profundo brilha

Output mostra 15 idx encadeados:
```
*1=https://a
*2=1+pi.example.com/v       ← idx 2 = idx 1 + ".pi.example.com/v"
*3=1+uth.example.com/v
*4=2+1/                      ← idx 4 = idx 2 + "1/" = "https://api.example.com/v1/"
*5=2+2/
*6=3+1/
*7=3+2/
*8=4+users/00                ← idx 8 = idx 4 + "users/00"
...
8 _0                          ← body: idx 8 + "0" = url completa
```

15 niveis hierarquicos serializados via encadeamento — body super
compacto.

### Trade-off claro

Pre-declaracao agressiva eh **dois-lados**:
- **GANHO** em hierarquia profunda (C7 -29% vs lab 20, C9 -61% vs lit)
- **PERDA** em hierarquia rasa (C1 +51%, C8 +11% vs lab 20) — header
  com decls que nao agregam

### Decisao registrada

Heuristica deveria **decidir entre estrategias** baseado em:
- Profundidade max da arvore PATRICIA
- Numero de afixos uteis sobrepostos
- Se "1 melhor" >= "soma da cadeia": usar single-afixo (lab 20)
- Senao: usar multi-afixo encadeado (este lab)

Pendencia para iteracao futura.

## Pendencias

- Heuristica meta que escolhe entre single vs multi-afixo
- Suffix encadeamento (atualmente so prefix encadeia)
- Cenarios reais (TPC-H, GitHub URLs, etc.) para validar curvas

## Status

- [x] Multi-afixo com pre-declaracao topologica
- [x] Encadeamento `*N=P+ext` funcional
- [x] 4/4 RT OK
- [x] C7/C9 brilham (-29% / -61% vs lit)
- [x] C1/C8 mostram trade-off honesto
