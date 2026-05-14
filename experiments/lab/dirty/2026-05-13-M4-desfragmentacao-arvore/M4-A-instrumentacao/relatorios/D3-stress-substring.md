# M4.A — Instrumentacao da arvore: D3-stress-substring

Strings unicas: 12
Tokens emitidos por alg16: 27

## 1. Frags alocados

- Total alocados: 15
- Usados em 2+ eids: **10**
- Usados 1x apenas: **5** (candidatos a inline)
- Nao-referenciados: 0 (criados pelo no fonte mas nunca usados)
- Inline potencial (frags 1x onde texto < idx): **0 bytes**

## 2. Distribuicao de idx por categoria

- Idx 1-9 (1 char): 9
- Idx 10-99 (2 chars): 6
- Idx 100+ (3 chars): 0
- Bytes em refs (ponderado por uso): **83**

## 3. Realocacao densa (idx baixos pros mais usados)

- Bytes atual: 83
- Bytes apos realocacao: 77
- **Economia teorica: 6 bytes**

## 4. Substrings compartilhadas (candidatos a no intermediario)

3 candidato(s) com R>=2:

| key (eid, tipo, len) | R | Lt | Lr | ganho implicito | ganho explicito | texto |
|---|---:|---:|---:|---:|---:|---|
| (4,P,12) | 2 | 12 | 6 | +10 | -8 | `web/users/00` |
| (1,P,12) | 2 | 12 | 4 | +6 | -12 | `api/users/00` |
| (1,S,13) | 2 | 13 | 4 | +6 | -13 | `/profile.json` |

## 5. Resumo dos limites teoricos

- **Inline frags 1x** (s/ tocar arvore): 0 bytes
- **Realocacao densa** (s/ tocar arvore): 6 bytes
- **No intermediario com idx implicito** (modifica arvore): 22 bytes
- **No intermediario com decl explicita** (M3-style): 0 bytes

Notas:
- Ganhos *implicitos* somam ocorrencias mas ignoram conflitos (varios candidatos podem competir).
- Ganhos *explicitos* descontam custo de declaracao (M3-style).
- *Inline* e *realocacao densa* sao ortogonais; podem somar.
- *No intermediario* modifica a arvore (M4.C).