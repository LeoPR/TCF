# M4.A — Instrumentacao da arvore: D1-emails-simples

Strings unicas: 12
Tokens emitidos por alg16: 25

## 1. Frags alocados

- Total alocados: 12
- Usados em 2+ eids: **12**
- Usados 1x apenas: **0** (candidatos a inline)
- Nao-referenciados: 0 (criados pelo no fonte mas nunca usados)
- Inline potencial (frags 1x onde texto < idx): **0 bytes**

## 2. Distribuicao de idx por categoria

- Idx 1-9 (1 char): 9
- Idx 10-99 (2 chars): 3
- Idx 100+ (3 chars): 0
- Bytes em refs (ponderado por uso): **64**

## 3. Realocacao densa (idx baixos pros mais usados)

- Bytes atual: 64
- Bytes apos realocacao: 62
- **Economia teorica: 2 bytes**

## 4. Substrings compartilhadas (candidatos a no intermediario)

6 candidato(s) com R>=2:

| key (eid, tipo, len) | R | Lt | Lr | ganho implicito | ganho explicito | texto |
|---|---:|---:|---:|---:|---:|---|
| (5,S,11) | 3 | 11 | 6 | +15 | -3 | `hotmail.com` |
| (4,P,4) | 2 | 4 | 6 | +10 | +0 | `ana@` |
| (9,S,9) | 3 | 9 | 4 | +9 | -7 | `yahoo.com` |
| (2,P,6) | 2 | 6 | 5 | +8 | -4 | `maria@` |
| (3,P,6) | 2 | 6 | 5 | +8 | -4 | `pedro@` |
| (1,P,5) | 2 | 5 | 4 | +6 | -5 | `joao@` |

## 5. Resumo dos limites teoricos

- **Inline frags 1x** (s/ tocar arvore): 0 bytes
- **Realocacao densa** (s/ tocar arvore): 2 bytes
- **No intermediario com idx implicito** (modifica arvore): 56 bytes
- **No intermediario com decl explicita** (M3-style): 0 bytes

Notas:
- Ganhos *implicitos* somam ocorrencias mas ignoram conflitos (varios candidatos podem competir).
- Ganhos *explicitos* descontam custo de declaracao (M3-style).
- *Inline* e *realocacao densa* sao ortogonais; podem somar.
- *No intermediario* modifica a arvore (M4.C).