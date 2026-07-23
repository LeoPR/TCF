# bench_perf — findings deferidos da review de limpeza [registro]

**Data**: 2026-07-23 00:30. Review de limpeza do `scripts/bench_perf/` (workflow, 5 agents,
23 findings). Os **clareamente-corretos** foram corrigidos no mesmo commit (hash de identidade
do plano, gzip real, robustez do comparador, dead-code, proveniência smoke, etc.). Estes ficaram
**deferidos** — pedem decisão de design, são acessórios, ou são latentes (não afetam o baseline
`.8` atual). Owner tria a prioridade.

## Deferidos

1. **`layers.py:40` — depth-aware double-count NÃO ligado (severidade alta)**. `_depth` nunca é
   incrementado; o breakdown por-camada (B3) soma o tempo dos candidatos perdedores (split/dict)
   no total → `wall_ns`/`share_of_layers` inflados, `por_profundidade` sempre `{0:…}`. É métrica
   SECUNDÁRIA (o tempo de encode principal, `point_ns`, é medido à parte por `probes`, não afetado).
   Fix correto exige envolver as fronteiras de recursão (`_struct_split_encode`/`_v2b_encode`) pra
   bumpar `_depth` — complexo e arriscado. **Interim honesto**: o breakdown inclui candidato perdedor;
   não tratar como puro-pipeline até rewire.

2. **`pivot.py:335+337` — gate strict de 2ª implementação é env-dependente**. O bloco `_STRICT`
   (orjson/msgspec/ujson) HARD-rejeita conforme a lib compilada instalada (orjson recusa int>64bit,
   contradizendo a regra N2 "int gigante = flag, não rejeição"; msgspec crasha por API diferente).
   Mesmo dataset passaria no `.8` e falharia no `.9` → **não-reproduzível**. MAS é o gate de
   "interseção de implementações" que o **owner desenhou** — decisão dele: remover, virar
   flag-advisory (registrar divergência sem rejeitar), ou pinar a lib. *(Latente: nenhuma lib strict
   instalada + synth limpo → não dispara hoje.)*

3. **`runner.py:245` — contention_ratio serial-vs-paralelo em B4**. O `solo` baseline usa o encode
   in-process (paralelo quando workers>1) vs `_worker_min_encode` serial. Afeta só B4 (concorrência),
   **fora do núcleo** (campanha). Medir um `solo` serial dedicado.

4. **`synth.py:40` — `low-entropy` trava cardinalidade em 12 (K vira no-op)**. `vocab[i%12]` limita a
   12 distintos independente de K. `low-entropy` não está nas formas do núcleo (flat-mixed/free-text/
   structured) → latente. Fix: escalar o vocab de low-entropy com K.

5. **`manifest.py:108` — `--check` não verifica compressor ausente**, apesar do help/docstring
   prometerem (a razão de existir do manifesto). Só checa git-dirty e seed. Adicionar a checagem de
   presença dos compressores declarados.

6. **`natures_9.py:78 + :118` — módulo ACESSÓRIO** (não importado pelo runner; ferramenta separada de
   evidência de natures). `ips()` gera IPs duplicados (`%255`/`//256`) quebrando "mesma escala entre
   naturezas"; `case_id` não qualifica escala nem emite seed/schema. Amarrado à **revisão estrutural
   de natures** já registrada em [direções §3](2026-07-22-2225-direcoes-pos-baseline-discutir-depois.md) —
   tratar junto.

Fonte: review `bench-perf-cleanup-review` (run wf_6c0705e6-034).
