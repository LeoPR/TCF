# INDEX — parâmetro de tolerância para float

**Aviso**: os `.tcf` que não são `.baseline` contêm valores **ajustados de
propósito**. O `roundtrip.json` prova que o FORMATO os preserva — não que são os
originais. O original está em `inputs/<coluna>.entrada.json`.

| coluna | pedido | casas | bytes | red% | cumpre? |
|---|---|---|---|---|---|
| sint-money | `{"rel": 0.01, "mode": "half-even"}` | 3 | 113 | 0.0 | CUMPRE |
| sint-money | `{"rel": 0.001, "mode": "half-even"}` | 4 | 113 | 0.0 | CUMPRE |
| sint-money | `{"abs": 0.005, "mode": "half-even"}` | 2 | 113 | 0.0 | CUMPRE |
| sint-money | `{"quantum": 0.01, "mode": "half-even"}` | 2 | 113 | 0.0 | CUMPRE |
| sint-money | `{"quantum": 0.1, "mode": "half-even"}` | 1 | 105 | 7.08 | CUMPRE |
| sint-money | `{"agg": "soma", "mode": "half-even"}` | 2 | 113 | 0.0 | CUMPRE |
| sint-money | `{"quantum": 0.1, "agg": "soma", "mode": "half-even"}` | 1 | 105 | 7.08 | CUMPRE |
| sint-money | `{"rel": 0.01, "mode": "half-up"}` | 3 | 113 | 0.0 | CUMPRE |
| sint-money | `{"rel": 0.01, "mode": "down"}` | 4 | 113 | 0.0 | CUMPRE |
| sint-money | `{"rel": 1e-09, "mode": "half-even"}` | 10 | 113 | 0.0 | CUMPRE |
| sint-money | `{"rel": 1e-15, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
| sint-money | `{"quantum": 0.03, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
| retail-UnitPrice | `{"rel": 0.01, "mode": "half-even"}` | 4 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"rel": 0.001, "mode": "half-even"}` | 5 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"abs": 0.005, "mode": "half-even"}` | 2 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"quantum": 0.01, "mode": "half-even"}` | 2 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"quantum": 0.1, "mode": "half-even"}` | 1 | 2910 | 21.03 | CUMPRE |
| retail-UnitPrice | `{"agg": "soma", "mode": "half-even"}` | 2 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"quantum": 0.1, "agg": "soma", "mode": "half-even"}` | 1 | 3028 | 17.83 | CUMPRE |
| retail-UnitPrice | `{"rel": 0.01, "mode": "half-up"}` | 4 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"rel": 0.01, "mode": "down"}` | 4 | 3701 | -0.43 | CUMPRE |
| retail-UnitPrice | `{"rel": 1e-09, "mode": "half-even"}` | 11 | 3685 | 0.0 | CUMPRE |
| retail-UnitPrice | `{"rel": 1e-15, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
| retail-UnitPrice | `{"quantum": 0.03, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
| wine-density | `{"rel": 0.01, "mode": "half-even"}` | 2 | 708 | 93.02 | CUMPRE |
| wine-density | `{"rel": 0.001, "mode": "half-even"}` | 3 | 1811 | 82.13 | CUMPRE |
| wine-density | `{"abs": 0.005, "mode": "half-even"}` | 2 | 708 | 93.02 | CUMPRE |
| wine-density | `{"quantum": 0.01, "mode": "half-even"}` | 2 | 708 | 93.02 | CUMPRE |
| wine-density | `{"quantum": 0.1, "mode": "half-even"}` | 1 | 20 | 99.8 | CUMPRE |
| wine-density | `{"agg": "soma", "mode": "half-even"}` | 5 | 10137 | 0.0 | CUMPRE |
| wine-density | `{"quantum": 0.1, "agg": "soma", "mode": "half-even"}` | 1 | 360 | 96.45 | CUMPRE |
| wine-density | `{"rel": 0.01, "mode": "half-up"}` | 2 | 708 | 93.02 | CUMPRE |
| wine-density | `{"rel": 0.01, "mode": "down"}` | 3 | 1789 | 82.35 | CUMPRE |
| wine-density | `{"rel": 1e-09, "mode": "half-even"}` | 9 | 10137 | 0.0 | CUMPRE |
| wine-density | `{"rel": 1e-15, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
| wine-density | `{"quantum": 0.03, "mode": "half-even"}` | — | — | — | RECUSA — tolerância não  |
