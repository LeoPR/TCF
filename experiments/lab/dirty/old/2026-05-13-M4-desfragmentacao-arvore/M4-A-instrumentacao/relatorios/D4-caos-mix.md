# M4.A — Instrumentacao da arvore: D4-caos-mix

Strings unicas: 12
Tokens emitidos por alg16: 25

## 1. Frags alocados

- Total alocados: 14
- Usados em 2+ eids: **8**
- Usados 1x apenas: **2** (candidatos a inline)
- Nao-referenciados: 4 (criados pelo no fonte mas nunca usados)
- Inline potencial (frags 1x onde texto < idx): **1 bytes**

## 2. Distribuicao de idx por categoria

- Idx 1-9 (1 char): 9
- Idx 10-99 (2 chars): 5
- Idx 100+ (3 chars): 0
- Bytes em refs (ponderado por uso): **61**

## 3. Realocacao densa (idx baixos pros mais usados)

- Bytes atual: 61
- Bytes apos realocacao: 53
- **Economia teorica: 8 bytes**

## 4. Substrings compartilhadas (candidatos a no intermediario)

3 candidato(s) com R>=2:

| key (eid, tipo, len) | R | Lt | Lr | ganho implicito | ganho explicito | texto |
|---|---:|---:|---:|---:|---:|---|
| (4,P,11) | 2 | 11 | 6 | +10 | -7 | `[b]*'foo'@4` |
| (1,P,11) | 2 | 11 | 4 | +6 | -11 | `[a]*'foo'@4` |
| (1,S,4) | 2 | 4 | 3 | +4 | -6 | `'@42` |

## 5. Resumo dos limites teoricos

- **Inline frags 1x** (s/ tocar arvore): 1 bytes
- **Realocacao densa** (s/ tocar arvore): 8 bytes
- **No intermediario com idx implicito** (modifica arvore): 20 bytes
- **No intermediario com decl explicita** (M3-style): 0 bytes

Notas:
- Ganhos *implicitos* somam ocorrencias mas ignoram conflitos (varios candidatos podem competir).
- Ganhos *explicitos* descontam custo de declaracao (M3-style).
- *Inline* e *realocacao densa* sao ortogonais; podem somar.
- *No intermediario* modifica a arvore (M4.C).