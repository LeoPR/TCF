# Proveniência — lacunas da frente de tipos (2026-07-25-1729)

**Fonte**: 100% sintético/determinístico, construído para **cobrir a matriz de tipos**, não
para representar dados reais. Nenhum download, nenhum CPF/CNPJ.

## Por que cada bloco existe

**A — rotas por tipo (9 casos)**: um exemplar mínimo de cada entrada que o dispatch trata de
forma diferente (`str`, `str+null`, `só null`, `[]`, `bool`, `bool alternado`, `int`, `float`,
`multi-col`). O objetivo é mapear a rota, então os casos são deliberadamente **pequenos** — o
que também é o regime onde o cabeçalho pesa.

**B — varredura do bool (8 casos)**: `n ∈ {1, 2, 4, 8, 16, 64, 256, 1000}`, padrão
determinístico (`i % 2`, `i % 3`, `(i*7) % 10 < 5`). Serve para localizar o **crossover**
contra JSON, não para medir compressão em dado realista.

**C — as lacunas (6 casos)**: as combinações que hoje caem no `.8H` — `bool+null` em 4
tamanhos, `multi+null`, `int+null`.

**D — namespace**: wires **construídos à mão** (`#TCF.8n`, `#TCF.8s`, `#TCF.8b{1,2,4,8}`) só
para registrar o que o decode aceita. Não são saídas do encoder.

## Limites declarados

- **Casos pequenos por construção.** As porcentagens do bloco A são de payload minúsculo, onde
  os 7 B de cabeçalho dominam. Não devem ser lidas como "o TCF é X% pior que JSON" em geral —
  o bloco B mostra a mesma métrica indo a −97% quando `n` cresce.
- **JSON compacto** (`separators=(",", ":")`, `ensure_ascii=False`) é a forma mais enxuta;
  comparar contra JSON indentado inflaria o ganho de graça. `null`, `true`, `false` são grafias
  **nativas** do JSON, então o baseline não é enviesado a favor do TCF nos casos com null/bool.
- **Sem gzip aqui.** O lab `2026-07-25-1630` já mediu esse eixo e registrou que a vantagem
  sobre JSON some sob gzip nesses tamanhos.
- **Uma métrica só**: bytes. Latência, memória e inspecionabilidade não entram.

## Reprodutibilidade

`python run.py` regenera todos os arquivos byte a byte — sem `random`, sem relógio, sem rede.
**Zero escrita em `src/tcf`**.
