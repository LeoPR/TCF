---
title: Volume strategy (N absoluto ou fraction)
type: task
status: OPEN
priority: 14
parent: 12-M-dataset-shaper
---

# Volume

`scripts/shaper/strategies/volume.py`

- `volume=100` → retorna exatamente 100 rows
- `volume=0.1` → retorna 10% das rows
- `volume=None` → retorna tudo (passthrough)
- `volume=0` → retorna vazio com aviso no trace

Usa seed do request para selecao quando precisa amostrar.

## Tarefas

- [ ] Implementar VolumeStrategy
- [ ] Registrar no pipeline
- [ ] Testes: N absoluto, fraction, None, 0, edge cases
