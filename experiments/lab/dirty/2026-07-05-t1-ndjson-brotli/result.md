# Result — T1: TCF+brotli vs NDJSON+brotli (o teste decisivo do posicionamento) [probatório]

**Data**: 2026-07-05 · **Tipo**: [probatório] · FORK (não toca `src/tcf`) · 6 datasets reais (Z:) ×
4 scales + caso forecast (download). `t1_bench.py` + `forecast_bench.py` + `summarize.py`.

Fecha o gate pendente desde 2026-06-21 ([transmissao-api-onde-tcf-importa.md](../notas/transmissao-api-onde-tcf-importa.md)):
toda evidência de "TCF ganha" era vs **CSV+brotli**; o concorrente TEXTUAL real é **NDJSON+brotli**
(padrão BigQuery/Elasticsearch/X API). Aqui mede-se, e mede-se também o **steelman** (JSON-colunar).

## Nota de reprodutibilidade (brotli)

`brotli` **nunca esteve pinado** no repo (nem `pyproject`/`uv.lock`/`requirements`; `git log -S`
vazio). Os labs antigos (EXP-008, staged-brotli) usavam um install ad-hoc que se perdeu. Reinstalado
`brotli==1.2.0` (**Brotli oficial do Google**, `github.com/google/brotli`). **Byte-paridade
confirmada**: adult n=3000 TCF+brotli = **21841**, idêntico ao lab staged-brotli → mesma
implementação, números históricos comparáveis. **Recomendação**: pinar `brotli` num extra `bench`
do pyproject (fecha fraqueza #8 dev-env / [feedback](../../../../../.claude...)).

## Fairness (pré-registrado)

Mesma data lógica, todas as colunas, sem sort. CSV com quoting correto. **NDJSON-str** (valores
string, fiel ao CSV) e **NDJSON-typed** (números sem aspas quando bijetivo = steelman NDJSON).
**JSON-colunar** `{col:[...]}` (chaves UMA vez = **steelman JSON máximo**, remove a maior fraqueza
do NDJSON). TCF v0.7 `encode`. **RT obrigatório**: `decode(tcf)==tabela` — passou em **24/24**.
Brotli q11 (melhor de cada) + sensibilidade q5 + gzip-9. `brotli==1.2.0`.

## Achado 1 — vs NDJSON+brotli (a pergunta LITERAL do T1): TCF vence, decisivo e universal

**TCF+brotli < NDJSON+brotli em 24/24 medições**, sem exceção. Agregado weighted (soma de bytes):

| scale | TCF % do NDJSON-typed | TCF % do CSV | TCF % do JSON-colunar |
|---|---|---|---|
| 1000 | **79.5%** | 88.1% | 97.5% |
| 3000 | **79.2%** | 87.9% | 98.9% |
| 5000 | **78.4%** | 87.1% | 98.4% |
| 10000 | **71.7%** | 80.3% | 91.1% |

Consistente em **gzip** e **brotli q5** (0 casos de perda/empate vs NDJSON em ambos). Logo o teste
decisivo **resolve a favor do TCF**: ~20–28% menos bytes que o concorrente textual padrão, não só
vs CSV. Confiança **Alta**.

## Achado 2 — vs JSON-colunar+brotli (o STEELMAN): vitória MARGINAL e dataset-dependente

A vitória sobre NDJSON é em parte porque **NDJSON repete as chaves em toda linha** — fraqueza que um
JSON colunar (`{col:[...]}`, chaves uma vez) remove. Contra esse steelman, **TCF perde em 10/24**:

| dataset (favor) | TCF % do JSON-colunar | veredito |
|---|---|---|
| adult (favorável, 15 col) | 74–75% | **vence forte, consistente** |
| tpch-lineitem (16 col) | 85–100% | vence, margem cresce com scale |
| receita (8 col) | 95–99% | vence apertado |
| ibge (8 col) | 88–105% | **empata/perde** em scales baixos |
| online-retail (8 col) | 97–112% | **perde** em 1k–5k, vence em 10k |
| **pessoas** (6 col, CPF/nomes) | 105–112% | **perde em todos** |

Padrão: TCF bate o JSON-colunar quando há **estrutura que o brotli não modela** — muitas colunas
categóricas low-card (adult) OU **cadência/sequência**. Perde em **high-card/poucas-colunas**
(pessoas: nomes+CPF quase sem redundância estrutural), onde tipar + chaves-uma-vez do JSON-colunar
já basta e o brotli faz o resto.

**Honestidade**: NÃO se pode afirmar "TCF+brotli vence JSON+brotli" em geral. Vence **NDJSON** (o
padrão real) sempre; vence o **JSON-colunar** só onde há estrutura (categórico largo ou cadenciado).

## Achado 3 — perfil DUPLO upload/download; download cadenciado é o nicho do steelman

Owner (2026-07-05): APIs têm perfil duplo — **upload** (request, economia de envio, tipicamente
<1KB) vs **download** (response, onde está o VOLUME). Forma típica de endpoint de forecast de série
temporal: request ~250B (TCF não ajuda); response = array de `{"ds":<timestamp horário>,"yhat":<float>}`
(horizon 1m ≈ 744 pontos). Medido (`forecast_bench.py`, forma **genérica/anonimizada** — rótulos
sintéticos; ecológico, viés TCF-favorável declarado):

| horizon | pts | envJSON+br | JSON-col+br | **TCF+br** | TCF % do JSON-col |
|---|---|---|---|---|---|
| 1d | 24 | 268 | 180 | 181 | **100.6%** (empata — payload <300B, TCF não ajuda) |
| 1w | 168 | 721 | 493 | 395 | **80.1%** (−20%) |
| 1m | 744 | 1967 | 1277 | 904 | **70.8%** (−29%) |

<small>(rótulos do envelope sintéticos/anonimizados; envJSON varia ~poucos bytes com os rótulos, o
comparativo TCF vs JSON-colunar independe deles.)</small>

TCF bate o **steelman JSON-colunar** aqui porque modela a cadência: o `ds` vira
`*24|\2026` / `*24+1|\00` / `*11|\37` / `*12|\38` (RLE do ano/mês/dia + delta da hora + o drift de
minuto :37→:38). **Nenhum layout JSON captura isso**. O `yhat` fica `!` (raw — floats sem redundância
estrutural, deixa pro brotli). Confirma também "<1KB TCF não ajuda" (1d empata).

→ O download cadenciado (séries temporais, forecast, logs) é onde a vitória sobre o steelman é
**robusta** — e é a direção de maior volume.

## Checklist anti-incidente (5 perguntas, CLAUDE.md)

1. **Real-world?** Sim — 6 datasets reais (Adult, IBGE, online-retail, receita, br-identidades,
   TPC-H) + forecast (ecológico).
2. **N≥5 fontes?** Sim (6 reais, fontes distintas).
3. **Sintético vs real?** Tudo real; forecast é ecológico (viés declarado).
4. **Viés declarado?** Sim — espectro favor=favorável/misto/desfavorável rotulado; forecast marcado
   TCF-favorável.
5. **Bytes absolutos ≥5%?** vs NDJSON: 20–28% (robusto). vs JSON-colunar: <10% agregado E **reverte**
   por dataset → NÃO robusto; não se claima vitória sobre "JSON" em geral.

**Status**: Achado 1 (vs NDJSON) **confirmada-empírica, confiança Alta**. Achado 2 (vs JSON-colunar)
**refutada-parcial** (vitória não-geral; localizada). Achado 3 (download cadenciado) confirmada-empírica
com viés declarado.

## Anomalia registrada

ibge 5000→5571 **não-monotônico** (45555→42872 bytes com MAIS linhas). Causa: 5571 = dataset
completo; decisões globais do encoder (V2-B dict / split / cadência) melhoram com N completo. RT ok.
Não é bug — TCF melhora com completude. (Não é streaming; encode vê a coluna toda.)

## O que T1 resolve e o que fica aberto

- **Resolve**: TCF+brotli vs NDJSON+brotli (decisivo, a favor). Fecha o gate de 2026-06-21.
- **Novo**: contra o JSON-colunar (steelman), a vitória é estrutura-dependente; localizada em
  categórico-largo e cadenciado.
- **Aberto**: T2 (break-even por volume — parcialmente visto: margem cresce com scale), T3
  (cardinalidade — pessoas mostra o limite), custo de decode (não medido), Parquet (invisível),
  zstd (não medido — mas é binário, fora do eixo textual/explicável).

## Frase de posicionamento (atualiza a nota de transmissão)

> Para transmissão, o TCF importa na direção **download** (response, onde está o volume), como
> **pré-processo textual antes do brotli**, em batch tabular >~1k linhas. Contra o padrão real
> **NDJSON+brotli**, o TCF entrega **20–28% menos bytes** em todos os datasets reais medidos (não só
> vs CSV). Contra o JSON textual mais compacto possível (colunar, chaves uma vez), a vantagem é
> **estrutura-dependente**: robusta em tabelas categóricas largas e — sobretudo — em payloads
> **cadenciados/sequenciais** (séries temporais, forecast: −29% vs JSON-colunar em 744 pontos, via
> RLE+delta da cadência que nenhum JSON captura); marginal ou negativa em dados high-card de poucas
> colunas. Upload pequeno (<1KB) e dados de alta entropia continuam fora do nicho.

## Cross-links

Fonte do gate: [transmissao-api-onde-tcf-importa.md](../notas/transmissao-api-onde-tcf-importa.md).
Prévio (vs CSV): [staged-brotli](../old/refuted/2026-06-16-staged-and-ordering-brotli/result.md).
Registry: [roadmap-hipoteses](../notas/roadmap-hipoteses.md). Diário: [2026-07-05](../notas/diario/2026-07-05.md).
