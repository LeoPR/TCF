# Provenance — datasets same-domain-ref do gate N>=5 (T-DATA-1) [apontamento]

Raw em `Z:/tcf-data/external/` (dado baixado NÃO entra no repo). Baixados 2026-07-01 por
[fetch_samedomain.py](fetch_samedomain.py). Somam-se a SNAP ca-GrQc + OpenFlights (B1) → **5 fontes**.
Morfologias diversas (contra overfit-a-grafo): esporte tabular, citação, comunicação.

## Novos (2026-07-01)
| dataset | local (Z:) | colunas same-domain | fonte / licença |
|---|---|---|---|
| **International football results** | `external/football-results/results.csv` (~3.7 MB, ~48k jogos) | `home_team` ~ `away_team` (seleções) | github.com/martj42/international_results (CC BY 4.0) |
| **SNAP cit-HepTh** | `external/snap-cit-hepth/cit-HepTh.txt` (~5.6 MB, 352k arestas) | from_paper ~ to_paper (citação) | snap.stanford.edu/data/cit-HepTh.html (acadêmico) |
| **SNAP email-Enron** | `external/snap-email-enron/email-Enron.txt` (~4.0 MB, 367k arestas) | from_node ~ to_node (email) | snap.stanford.edu/data/email-Enron.html (acadêmico) |

Não baixado: tennis-atp (JeffSackmann/tennis_atp) — URL 404 em 2026-07-01 (repo movido/indisponível).
Não foi necessário (5 fontes já cobrem o gate).

## Regenerar
`python experiments/lab/dirty/2026-06-27-gdict-b2-prototype/fetch_samedomain.py` (idempotente; skip
se já existe). Grafos amostrados (cap 40k arestas) na medição por velocidade — ver
[run_gate.py](run_gate.py).

## Uso
Gate: [gate-result.md](gate-result.md). Veredito: cross-dict (B2) falha o gate (1/5 ≥15%); o achado
robusto é o dict per-col high-card (H-DICT-HIGHCARD, 4/5).
