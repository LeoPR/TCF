# Proveniência das entradas

Sintéticas **construídas para vistoria** (viés declarado: material de FORMA/contrato, não medida
de ganho — anti-incidente 2026-05-21).

- `inputs/01-cadastro-ragged.json` — cadastro API-like: `email`/`telefone` opcionais no topo,
  `complemento` opcional DENTRO do objeto `endereco` (1:1). CPFs placeholder repetidos
  (`111.111.111-11`…), **nunca DV-válidos** (§2.3).
- `inputs/02-telemetria-ragged.json` — leituras com campo `erro` RARO (2/8) — o regime "campo só
  aparece quando acontece", típico de telemetria/logs.
- `inputs/03-pedido-aninhado-ragged.json` — `cupom` opcional; `itens` opcional com a distinção
  TRIPLA (Ana=cheio, Carla=`[]` vazio, Daniel=AUSENTE); `obs` opcional dentro de ELEMENTOS do array
  (mask por instância).
- M1/M4 (study.py) — gerados com seed fixa (`random.Random(20260715)`), regimes de frequência
  declarados (raro 1/20; alternado 1/2 = pior caso RLE; API-like 90%/50%/5%).

Nenhum dado real neste estudo (a validação em massa/real fica pro gate do weld, PW3/PW4 — mesma
esteira do weld anterior: fuzz + TPC-H + receita-cnpj).
