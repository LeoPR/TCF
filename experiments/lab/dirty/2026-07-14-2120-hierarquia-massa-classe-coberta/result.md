# Resultado — fuzz em massa da classe coberta (weld hierárquico)

**[probatório]** 8000 documentos aleatórios (seed fixa 20260714), RT byte-exato
`decode(encode_hierarchical(recs)) == recs`: **8000/8000, 0 falhas**. Cobertura exercitada:
5263 com arrays vazios, 2379 com ≥2 arrays irmãos, 1609 com arrays aninhados. Números:
[outputs/01-fuzz.txt](outputs/01-fuzz.txt).

## Leitura

O **óbvio está fixado**: a classe que o weld cobre (objetos de schema uniforme, escalares string,
`{}` 1:1, `[]` 1:N com `#count`, arrays vazios/irmãos/aninhados) sobrevive a fuzz em massa sem
regressão. Isto complementa os testes-clássicos pinados em `tests/test_hierarchical_rt.py` (que
travam casos NOMEADOS): aqui é volume + aleatoriedade dentro do mesmo contrato.

## Encaminhamento

- **Fecha** a etapa "classe coberta" do weld (funcionalidade + robustez). Nada a mudar no core.
- Candidato a **promover** a fuzz determinístico para `tests/` como property-test seedado
  (mesma seed → sem flakiness) — decisão do owner (fecha o ticket com um guarda permanente).
- Próximas ETAPAS de funcionalidade (owner escolhe, uma de cada vez): ragged (máscara de presença),
  tipos/null (deixado pro fim pelo owner), N-raízes, ADR do weld. Otimizações (bloco L3) só no fim.

`confianca: Alta` p/ a classe coberta (fuzz + clássicos pinados). Escopo declarado: só a classe
coberta; fora dela o contrato é fail-loud (não testado como RT aqui).
