# 2026-08-09-2228 — bateria multi-vetor dos encaixes de agora

Pedido do owner: o melhor pra AGORA no balanco bytes x CPU x memoria x online-ness,
com a regra **win-win = default; trade = um default + a melhor versao de cada
qualidade** (fechar o 1.0). Conclusoes: [`result.md`](result.md).

## Como rodar

```
python run.py
```

RT verde em todos os candidatos de todos os casos. CPU por rodadas INTERCALADAS
(mediana de 5, CV reportado); memoria por tracemalloc (pico); online-ness por analise
estrutural do corpo (fundamentada nas sondas — o split e' um multi-col embutido).

## Guia de nomes

| onde | o que |
|---|---|
| `inputs/e2-*.json` / `inputs/e1-*.json` | amostras dos inputs por caso |
| `outputs/e2-mes-ciclico.tcf` | wire do E2 vencedor (`*600~1,...,1,-11|`) — decodavel HOJE |
| `outputs/bateria.json` | todas as medicoes em maquina |

## Os candidatos

- **E2 sem-dedup**: corpo literal + uniforme/periodico soldados; encoder-only (a
  gramatica ja decodifica — provado por sonda antes da bateria)
- **E1 split na flat**: `_struct_split_encode` (ADR-0026) medido como candidato da rota
  single-col
- **SPEC mensal (A4)**: confirmacao de CPU/mem do espelho vs spec ordinal atual

`src/tcf` NAO foi tocado.
