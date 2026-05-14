# M4.A — Instrumentacao da arvore (sem mexer no alg16)

## Proposito

Medir limites teoricos de varias tecnicas de desfragmentacao
antes de implementar qualquer uma. Identifica onde vale a pena.

## Saidas

- `analise.py` — script de medicao
- `relatorios/<dataset>.md` — relatorio por dataset
- `relatorios/_resumo.md` — consolidado
- `conclusoes.md` — analise dos numeros

## Como rodar

```bash
cd 2026-05-13-M4-desfragmentacao-arvore
python M4-A-instrumentacao/analise.py
```

## Resultado resumido

| Tecnica | Ganho teorico (D1-D4 total) |
|---|---:|
| Inline frags 1x | 1B |
| Realocacao densa de idx | 17B |
| No intermediario implicito | ate' 114B |
| No intermediario explicito | 0B (M3 confirmado) |

Baseline M1.E: 676 bytes.

Conclusao: ver `conclusoes.md`.
