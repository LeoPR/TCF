# Proveniência — tag `n` weldada (2026-07-25-1746)

**Fonte**: 100% sintético/determinístico. É a **mesma matriz** do lab `2026-07-25-1729`,
reexecutada depois do weld, mais 4 casos que só passaram a existir com a generalização
(`C7` int sequencial, `C8` float+null, `C9` negativos, `C10` int grande). Reusar a matriz é
deliberado: torna o antes/depois comparável linha a linha.

## Blocos

- **A (9)**: um exemplar mínimo de cada rota do dispatch. Pequenos **por construção** — o
  objetivo é mapear rota, e é também o regime onde os 7 B de cabeçalho pesam.
- **B (8)**: bool com `n ∈ {1,2,4,8,16,64,256,1000}` — localiza o crossover contra JSON.
- **C (10)**: null e número, incluindo os casos que estavam no `.8H` antes do weld.
- **D**: wires **construídos à mão** (`#TCF.8n`, `#TCF.8s`, `#TCF.8b{1,2,4,8}`) só para
  registrar o que o decode aceita. Não são saídas do encoder.

## Baselines

- **`antes`** = `_encode_hierarchical` (a rota que toda coluna tipada tomava). Reconstruído,
  não copiado do lab anterior — se o `.8H` mudar, o número acompanha.
- **JSON** = `json.dumps(separators=(",", ":"), ensure_ascii=False)`, a forma mais enxuta.
  `null`, `true`, `false` e números são grafias **nativas** do JSON, então o baseline não é
  enviesado a favor do TCF em nenhum dos blocos.

## Limites declarados

- **Métrica única: bytes.** Sem gzip (medido no lab `1630`), sem latência, sem memória.
- **Casos de A/B/C pequenos** em boa parte. As porcentagens positivas contra JSON vêm quase
  todas daí — o mesmo `C7-int-100` é −91%. Não ler "+129%" como "o TCF é pior que JSON".
- **Números sintéticos**, não distribuição real. `C7` é `range(100)` (o melhor caso possível
  para o seq-RLE) e `C10` são dois inteiros grandes consecutivos. Nenhum representa uma
  coluna numérica real — só cobrem as formas.
- **Sem multi-col + null** resolvido: continua no `.8H`, e está na tabela como tal.

## Reprodutibilidade

`python run.py` regenera todos os arquivos byte a byte — sem `random`, sem relógio, sem rede.
**Zero escrita em `src/tcf`** (o weld está versionado à parte; suíte 959 passed).
