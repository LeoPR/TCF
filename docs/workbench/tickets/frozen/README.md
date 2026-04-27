# Tickets Congelados — Futuro Trabalho

Os tickets desta pasta foram **congelados em 2026-04-10** quando
decidimos voltar a prancheta e comecar o projeto pelos **dados**
(datasets canonicos) em vez de pelo formato.

## Por que congelados (nao apagados)

Eles representam pesquisa e reflexao validas. Nao sao errados —
apenas **prematuros**. Ainda nao sabemos se vamos precisar deles.
A decisao e:

1. **Primeiro:** organizar datasets canonicos (TPC-H, Adult) — `open/M-datasets-setup.md`
2. **Segundo:** implementar ferramentas minimas de derivacao (CSV, JSONL, SQLite)
3. **Terceiro:** definir pergunta cientifica nuclear (provavelmente STATS-based)
4. **So entao:** decidir quais destes tickets sao relevantes

Muitos destes tickets provavelmente nao entrarao na v1 do paper,
mas podem virar **apendices de futuro trabalho** ou **trabalhos separados**.

## O que cada grupo representa

### Formato TCF (especifico demais para a v1)
- `H-advanced-encodings.md` — delta, FOR, value encoding (SQL Server style)
- `H-streaming-encoder.md` — streaming/chunked encoder
- `H-token-friendly-format.md` — otimizar formato para BPE
- `H-compression-layers.md` — L4/L5 hipoteticos
- `H-smart-rounding.md` — precisao com % de erro
- `P-schema-extension.md` — PK, FK, constraints no header
- `P-data-types.md` — base64, binario, datas
- `P-rle-vs-gzip.md` — RLE agrega valor apos gzip?

### Experimentos especificos (muita ambicao)
- `E-benchmark-plan.md` — 332 combos (plano antigo)
- `E-code-generation.md` — LLM gera codigo validador
- `E-direct-conversion.md` — SQL → TCF direto
- `E-http-protocol.md` — TCF como protocolo HTTP
- `E-llm-decompress.md` — LLM descomprime TCF → CSV
- `E-memory-profiling.md` — peak RAM
- `E-prompt-presentation.md` — idioma, decoracao, wording
- `E-qualitative-reasoning.md` — perguntas aproximadas
- `E-scale-progression.md` — DONE como finding, ticket nao precisa
- `E-speed-tradeoffs.md` — pareto accuracy × latency
- `E-standalone-use-cases.md` — TCF sem LLM
- `E-token-count.md` — tokens reais via tiktoken

### Metodologia e pesquisa
- `G-utility-analysis.md` — guia master de 10 dimensoes
- `M-llm-scope.md` — mapa "onde LLM ajuda"
- `M-stability-testing.md` — N>=3 runs
- `M-tokenizer-validation.md` — 3 fontes de verdade de tokens
- `P-G33-metodologia.md` — CoT, PoT, repeticoes
- `P-G34-dados-reais.md` — superado pela nova fase de datasets
- `P-G35-modelos-llm.md` — selecao de modelos
- `P-competing-formats.md` — comparacao com TOON
- `P-question-bank-review.md` — banco de perguntas

### Engenharia / entregaveis
- `T-G41-cli-lib.md` — pip package
- `T-G42-input-adapters.md` — SQLite, Parquet adapters
- `T-multi-lang.md` — decoders JS, C, Go
- `T-figures-analysis.md` — figuras do paper

### Ja resolvido
- `H-G30-hiperparametros.md` — DONE com findings F60-F63

## Reatividade

Se durante a fase de datasets descobrirmos que algum destes tickets
e **essencial** (e nao so ambicioso), movemos de volta para `open/`
com justificativa clara.

**Criterio de retorno:** "este ticket bloqueia a pergunta cientifica
principal?" Se sim, move. Se nao, fica congelado.
