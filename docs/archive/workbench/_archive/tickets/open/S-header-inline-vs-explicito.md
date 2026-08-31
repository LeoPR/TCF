---
title: Decisão automática inline vs explícito para declarações
type: study
status: open
priority: high
created: 2026-05-10
---

## Contexto

Os labs 18 e 24 (dirty) implementaram dois esquemas distintos de
declaracao de fragmento, com trade-offs opostos:

### Esquema A — INLINE (lab 18, lab 23)

A primeira ocorrencia de um fragmento eh declarada **dentro do body**:
```
red                    ← linha 1, literal
=1                     ← linha 2, repete linha 1
*green                 ← linha 3, declara inline (idx implicito = 3)
=3                     ← linha 4, refere linha 3 (= green)
```

Idx eh implicito = numero da linha.

**Vantagens**:
- Sem header explicito (economiza bytes)
- Numero da linha ja eh idx natural

**Desvantagens**:
- Nao permite encadeamento `*N=P+ext` (precisa de idx nomeado)
- Idx pode crescer (linha 1000 = idx 1000 = 4 chars)

### Esquema B — EXPLICITO (lab 24)

Declaracoes ficam num **header separado**, com idx nomeado:
```
*1=https://api.example.com/v1/
*2=1+users/0
*3=1+orders/0
1                      ← body comeca, refere idx 1
3 _0042                ← idx 3 + mid
```

**Vantagens**:
- Permite encadeamento `*N=P+ext` (essencial para hierarquia)
- Idx pequeno (limitado ao numero de fragmentos, nao linhas)

**Desvantagens**:
- Header custa bytes extras (`*N=` = 3B + idx digits)
- Em datasets sem hierarquia, eh puro overhead

## Resultado empirico (lab 24)

| Cenario | inline (lab23) | explicito (lab24) | diff |
|---------|---------------:|------------------:|-----:|
| E5 categoricas-100 | 332B | 348B | +16B (+4.8%) |
| E1 emails-100 | 815B | 823B | +8B (+1.0%) |
| E3 codigos-100 | 622B | 630B | +8B (+1.3%) |
| E7 urls-1000 | 14443B | **7103B** | **-7340B (-50.8%)** |

Padrao: explicito perde marginalmente onde inline ganha sozinho;
ganha muito onde encadeamento eh aplicavel.

## Decisao automatica

Encoder deveria escolher entre inline e explicito com base em:

```python
def choose_scheme(useful_fwd):
    # Conta nos com ancestral util na lista
    chained = sum(
        1 for n, _, _, _ in useful_fwd
        if any(
            other != n and full.startswith(other_full)
            for other, other_full, _, _ in useful_fwd
        )
    )
    if chained >= 2:
        return "explicit"  # encadeamento vale a pena
    return "inline"
```

Heuristica simples: se ha pelo menos 2 nos uteis com relacao
ancestral entre si (= candidato a encadeamento), usar explicito.
Caso contrario, inline.

## Esquema misto (mais complexo, talvez nao valha)

Ainda eh possivel um misto:
- Decls **isoladas** (sem ancestrais): inline com idx implicito
- Decls **encadeadas**: header explicito com `*N=P+ext`

Mas isso confunde o esquema de idx (alguns implicitos por ordem,
outros explicitos por nome). Provavelmente nao vale a complexidade.

## Quando implementar

Direto no port do lab 24 para clean prototype (`EXP-007-...`):
- Implementar logica de escolha automatica
- Validar 7/7 RT em todos os cenarios
- Comparar bytes vs lab 23 (inline puro) e lab 24 (explicito puro)
- Ganho esperado: tomar o melhor dos dois (tabela acima)

## Relacionado

- Lab 18 dirty — esquema A inline
- Lab 24 dirty — esquema B explicito
- Lab 21 dirty — primeira tentativa de encadeamento
- [H-compression-v04-roadmap](H-compression-v04-roadmap.md) — Proposta H Affix-DICT
- [S-idx-universal-linha-fragmento](S-idx-universal-linha-fragmento.md)
  — proposta de unificacao (resolveria isso elegantemente)
