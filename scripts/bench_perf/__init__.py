"""bench_perf — baseline de PERFORMANCE do TCF (schema perf-baseline-09/v1).

Artefato distinto do `bench_evidencia*` (regua de BYTES do `.8`, que fica
intocada e reproduzivel). Aqui se mede o `.8` COMO ELE E', de fora: nenhuma
instrumentacao entra em `src/tcf` (decisao do owner, 2026-07-21). Os pontos de
juncao das camadas sao nomes globais de modulo resolvidos em tempo de chamada,
entao o perfil por camada e' obtido por wrappers do harness — sem tocar um byte
do core, sem risco a byte-canonicidade.

Modulos:
  probes.py  sondas (amostras cruas, wall+cpu, tiers com MDE declarado)
  pivot.py   o dataset como pivo + derivacoes (json/csv/aninhado) + gates de classe
"""

__all__: list[str] = []
SCHEMA = "perf-baseline-09/v1"
