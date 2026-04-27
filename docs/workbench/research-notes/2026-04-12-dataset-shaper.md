# Pesquisa 2026-04-12: Dataset Shaper — Sampler Multidimensional

## Motivacao

Antes de testar TCF ou qualquer formato, precisamos de um
**Dataset Shaper** — componente que extrai subsets controlados
dos datasets canonicos segundo varias dimensoes independentes.

Sem isso, cada experimento reinventa "como pegar 100 rows",
e nao conseguimos testar sistematicamente escalas, complexidades,
estratificacoes e graus de compressibilidade.

## Decisoes do usuario (2026-04-12)

| Decisao | Resposta |
|---------|---------|
| D1 Escopo | Minimo viavel, mas modular para escalar depois |
| D2 Difficulty cache | Sob demanda, gera uma vez e cacheia permanente |
| D3 Join level | So `normalized` vs `flat` por enquanto |
| D4 Schema complexity | Niveis nomeados: minimal, core, chain, full |
| D5 Metrica dificuldade | Score de raridade por quantil |
| D6 Validacoes | Pesquisar gaps + combinatorial pairwise |
| D7 Dataset arranque | Adult primeiro, TPC-H depois |

## Dimensoes do shaper

| Dimensao | Parametro | Tipo | Default |
|----------|-----------|------|---------|
| Volume | `volume` | int ou float(0-1) | None (tudo) |
| Schema | `schema` | str ou list[str] | "full" |
| Join level | `join_level` | "normalized" ou "flat" | "normalized" |
| Order | `order` | "natural", "random", "sorted:col", "reverse:col" | "natural" |
| Seed | `seed` | int | 42 |
| Stratification | `stratify_by` | str (nome de coluna) ou None | None |
| Compressibility | `compressibility_range` | tuple(float, float) ou None | None |

## Pipeline (ordem fixa)

```
1. schema_filter     → seleciona tabelas/colunas
2. join_resolver     → normalized ou flat
3. compressibility   → score + filter (se solicitado)
4. stratify          → amostragem estratificada (se solicitado)
5. volume_sampler    → corta para N ou %
6. orderer           → reordena saida
7. ── retorna ShapeResult ──
```

Ordem importa: compressibility filtra antes do volume, stratify antes
do corte final, ordering e sempre ultimo.

## Conflitos identificados e resolucoes

| Conflito | Resolucao |
|----------|-----------|
| Volume pequeno + muitos estratos | Best effort + aviso no trace |
| Flat + schema minimal | Flat sem efeito (1 tabela) |
| Difficulty range estreito + volume grande | Difficulty filtra primeiro, volume corta |
| Volume 0 | Retorna vazio + aviso |

## Metrica de compressibility

Score de raridade por row:
```
score(row) = sum(-log2(freq(val_col) / total) for col in categoricals)
```

Rows com valores raros = score alto = mais dificeis de comprimir.

Bucketing por quantil (0.0 = mais facil, 1.0 = mais dificil):
```python
compressibility_range=(0.0, 0.3)  # 30% mais compressiveis
compressibility_range=(0.7, 1.0)  # 30% menos compressiveis
```

Cache em `Z:/tcf-data/shaper-cache/{dataset}/{table}_rarity.json`.
Invalidacao por hash do DB file.

## Estrutura no codigo

```
scripts/shaper/
  __init__.py          → expoe Shaper, ShapeRequest, ShapeResult
  request.py           → dataclass ShapeRequest + validacao
  result.py            → dataclass ShapeResult
  pipeline.py          → executa strategies em ordem fixa
  strategies/
    __init__.py
    schema.py          → filter por tabelas/colunas
    join.py            → normalized vs flat
    compressibility.py → score de raridade + filter
    stratify.py        → amostragem estratificada
    volume.py          → N absoluto ou fraction
    ordering.py        → natural, random, sorted, reverse
  cache.py             → cache de scores em disco
```

## Interface do Strategy (protocol)

```python
class Strategy(Protocol):
    def apply(
        self,
        reader: DatasetReader,
        tables: dict[str, list[dict]],
        request: ShapeRequest,
        trace: list[str],
    ) -> dict[str, list[dict]]:
        ...
```

Cada strategy recebe tabelas + request, retorna tabelas transformadas,
e appenda steps ao trace. Pipeline chama em ordem fixa.

## Modularidade para extensao futura

Adicionar nova dimensao (ex: `type_richness`, `null_density`):
1. Criar `scripts/shaper/strategies/new_dim.py`
2. Implementar Protocol `Strategy`
3. Adicionar campo em `ShapeRequest`
4. Registrar no pipeline (1 linha em `pipeline.py`)

Zero mudanca nos strategies existentes.

## Validacoes planejadas

**Invariantes:**
- volume=1.0 → retorna exatamente tudo
- volume=0.0 → vazio ou erro claro
- same request + same seed → same result (determinismo)
- resultado nunca tem MAIS rows que solicitado
- trace contem TODAS as steps executadas

**Direcionalidade:**
- compressibility low → score medio menor que high
- stratify_by com K valores → pelo menos 1 row por valor (se volume permite)

**Pairwise (NIST):**
- Todas combinacoes 2-way de (volume × schema × order) devem funcionar

## Sequencia de implementacao

**Minimo viavel (Fase 1.5a):**
tickets 13-18: request + pipeline + volume + schema + ordering + e2e test

**Extensao (Fase 1.5b):**
tickets 19-22: stratify + compressibility + join_level + combined tests

## Referencias

- [Sampling Methods — Scribbr](https://www.scribbr.com/methodology/sampling-methods/)
- [NIST Combinatorial Testing](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software)
- [Pairwise Testing — CrossLake](https://crosslaketech.com/how-to-use-pairwise-testing/)
- [Model Quality Data Slicing — Medium/Kästner](https://ckaestne.medium.com/model-quality-slicing-capabilities-invariants-and-other-testing-strategies-27e456027bd)
- [Framework for Stratification Estimation — arxiv 2406.07320](https://arxiv.org/abs/2406.07320)

## Nota: relacao com TCF

O shaper **nao sabe** do TCF. Ele retorna estruturas Python genericas.
O TCF (futuro) vai consumir essas estruturas. Sao softwares separados
que colidem nos testes de "fazer/desfazer" (encode/decode roundtrip).

Duas implementacoes independentes que, quando colidirem, validam uma a outra.
