# M4.A — Resumo consolidado

Limites teoricos de economia por tecnica, sem implementar.

| Dataset | Frags | Usados 2+ | Usados 1x | Inline | Realoc densa | Intermed (impl) | Intermed (expl) |
|---|---:|---:|---:|---:|---:|---:|---:|
| D1-emails-simples | 12 | 12 | 0 | 0 | 2 | 56 | 0 |
| D2-emails-quote-id | 18 | 9 | 5 | 0 | 1 | 16 | 0 |
| D3-stress-substring | 15 | 10 | 5 | 0 | 6 | 22 | 0 |
| D4-caos-mix | 14 | 8 | 2 | 1 | 8 | 20 | 0 |
| **TOTAL** | — | — | — | **1** | **17** | **114** | **0** |

## Baseline para comparacao

- M1.E nos canonicos: 676 bytes
- M2.A nos canonicos: 666 bytes (-10 vs M1.E)
- M3.A/M3.B: 676 (sem ganho liquido)

## Como ler

- **Inline frags 1x**: frags alocados mas usados 1x onde texto inline custa menos que o idx. Ganho real se implementarmos idx-por-demanda (M4.B).
- **Realocacao densa**: idx baixos (1 char) pros mais usados, altos (2 chars) pros menos usados. Ortogonal ao inline.
- **No intermediario (implicito)**: limite superior se criassemos nos compartilhados com idx implicito (sem preambulo). Ignora conflitos.
- **No intermediario (explicito)**: idem mas com declaracao explicita estilo M3. Net real ja' descontado custo de decl.

Ganhos sao **limites teoricos** — implementacao real
pode ficar abaixo por conflitos entre tecnicas.