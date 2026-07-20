"""llm_query — gadget auxiliar (NAO TCF-core): geracao de QUERY DE CONSULTA por LLM.

Produto sobrevivente do antigo harness `llm-benchmark/` (v0.5). Foco: dado um
schema/pergunta de negocio + payload TCF, a LLM PRODUZ uma query executavel
(SQL principalmente; tambem codigo polars/pandas em run_m5) que o runner executa
e pontua. Isto e' a "Linha B" (query-gen) — distinta da "Linha A" (jogar dados
na LLM pra deduzir), que a literatura ja' refutou e foi arquivada em
`old/llm-benchmark/` (2026-07-19).

NAO faz parte do pacote `tcf-format` (fica fora do wheel/sdist; dev-only sob src/).
Consome `tcf` (encode/EncodeConfig), `scripts/dataset_reader`, `tests/fixtures`.
Os runners (`run_*.py`) sao scripts standalone: cada um insere o proprio dir +
repo-root no sys.path e importa os irmaos flat (`from llm_eval... import`,
`import data_sources`, `from run_m1_codegen import ...`).

Roadmap: T-RECOVER-LLM-SCHEMA-MODE — spin-off recomendado quando maduro.
"""
__all__: list[str] = []
