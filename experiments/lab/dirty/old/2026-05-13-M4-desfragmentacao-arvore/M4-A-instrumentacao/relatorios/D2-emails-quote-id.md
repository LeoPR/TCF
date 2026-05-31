# M4.A — Instrumentacao da arvore: D2-emails-quote-id

Strings unicas: 12
Tokens emitidos por alg16: 27

## 1. Frags alocados

- Total alocados: 18
- Usados em 2+ eids: **9**
- Usados 1x apenas: **5** (candidatos a inline)
- Nao-referenciados: 4 (criados pelo no fonte mas nunca usados)
- Inline potencial (frags 1x onde texto < idx): **0 bytes**

## 2. Distribuicao de idx por categoria

- Idx 1-9 (1 char): 9
- Idx 10-99 (2 chars): 9
- Idx 100+ (3 chars): 0
- Bytes em refs (ponderado por uso): **55**

## 3. Realocacao densa (idx baixos pros mais usados)

- Bytes atual: 55
- Bytes apos realocacao: 54
- **Economia teorica: 1 bytes**

## 4. Substrings compartilhadas (candidatos a no intermediario)

2 candidato(s) com R>=2:

| key (eid, tipo, len) | R | Lt | Lr | ganho implicito | ganho explicito | texto |
|---|---:|---:|---:|---:|---:|---|
| (2,S,12) | 2 | 12 | 6 | +10 | -8 | `42@gmail.com` |
| (1,S,10) | 2 | 10 | 4 | +6 | -10 | `@gmail.com` |

## 5. Resumo dos limites teoricos

- **Inline frags 1x** (s/ tocar arvore): 0 bytes
- **Realocacao densa** (s/ tocar arvore): 1 bytes
- **No intermediario com idx implicito** (modifica arvore): 16 bytes
- **No intermediario com decl explicita** (M3-style): 0 bytes

Notas:
- Ganhos *implicitos* somam ocorrencias mas ignoram conflitos (varios candidatos podem competir).
- Ganhos *explicitos* descontam custo de declaracao (M3-style).
- *Inline* e *realocacao densa* sao ortogonais; podem somar.
- *No intermediario* modifica a arvore (M4.C).