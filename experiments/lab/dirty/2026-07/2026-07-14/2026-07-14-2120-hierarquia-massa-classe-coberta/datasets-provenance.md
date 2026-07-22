# Proveniência das entradas

Sintéticas **geradas por seed fixa** (não há `inputs/` em arquivo — o gerador está em
`fuzz.py`, `random.Random(20260714)`, determinístico e reproduzível). Material de ROBUSTEZ
(cobertura da classe), não medida de ganho.

- **Gerador**: `_make_schema` (schema uniforme por documento, profundidade 0–3) + `_emit`
  (materializa cada registro segundo o schema). Sem ragged por construção (schema fixo por doc).
- **Escalares**: mistura proposital de numérico-como-string, baixa-cardinalidade (@dict/RLE),
  com separadores `, | \ : #` (escaping) e texto livre variável — para exercitar os caminhos do
  compressor L1 sob a hierarquia.
- **Multiplicidades**: arrays com 0..4 elementos (inclui VAZIO), para exercitar `#count` e o
  caminho de array vazio.
- **Viés declarado**: fica DENTRO da classe coberta de propósito — não gera null/tipos/ragged/N:N
  (esses são fail-loud, testados em `tests/test_hierarchical_rt.py`, não aqui). É teste de robustez
  do contrato atual, não de expansão de escopo.
