# 2026-07-06-2354 — motor spec_bin (escape + RLE/bitstream + exceções)

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · nota-mãe
[tipos-como-specs](../notas/tipos-como-specs.md) · segue o estudo
[boolean-datasets](../2026-07-06-2332-boolean-spec-datasets/result.md). Design do owner (2026-07-06):
"deixar um motor preparado e pensar na realidade dos dados depois".

## Estado

- **era**: spec binária dependia de catálogo de variantes (bool true/false, 1/0, …).
- **foi**: motor com **escape** (sem catálogo) + 2 codificações de corpo + overlay de exceções.
- **é**: **escape** = os 2 valores mais comuns SÃO o domínio (guardados 1×, afixo-comprimidos: `male→fe1`).
  Corpo = bit-stream; o motor testa **RLE (textual/explicável)** vs **packed (binário, N/8)** e escolhe o
  menor. **Overlay de exceções** (99% dominantes + raros null/other) lossless. Tudo RT-OK.
- **será**: enum-k (k>2); bitstream real na camada binária (V2-L); ligar autoridade (typed→canonicaliza).

## Achados (medidos)

1. **Crossover ordem×codificação** (N=1000): ordenado (2 runs) → RLE 12B; skew 99/1 (21 runs) → RLE 95B;
   bloco/alternado/aleatório (100–1000 runs) → packed 125B. **Poucos runs → RLE; muitos → packed.**
2. **Dado REAL vence com packed**: adult.sex 97KB→**6KB (16×)**, l_linestatus 48KB→7.5KB, matriz_filial
   72KB→25KB — porque o dump vem **espalhado** (17–21k runs em 48–200k linhas). RLE só ganharia se
   **ordenado/agrupado** pela coluna (export sorted, índice clusterizado).
3. **Exceções** (99% male/female + null/other): overlay (posição,valor) esparsa; bit-stream cobre 100%,
   overlay corrige. RT-OK, 199B (N=1000). = def-level (Ciclo 1c) + binário.
4. **Domínio afixo**: `encode(['male','female'])='male\nfe1\n'` — o 2º relaciona ao 1º pelo OBAT (o owner previu).

## Tensão explicabilidade (o "manter a quebra")

- **RLE** (`*N|male`) = textual, **grupos visíveis** (pilar explicabilidade), mantém a quebra.
- **packed** = binário, **opaco** (é V2-L: representação binária INTERNA do TCF, header textual roteia).
- O motor escolhe por bytes; política sugerida: **preferir RLE quando fica perto** (mantém a quebra); ir
  binário quando o ganho é grande (real: 6KB vs 86KB → binário justificado).

## Arquivos

- `bin_engine.py` — motor: induce (2 dominantes), encode/decode (bits+overlay), rle/packed/textbits, best_body.
- `run.py` — afixo + distribuições + exceções + colunas reais. `python run.py` regenera `artifacts/`.
- `artifacts/` — `00-resumo` · `01-motor-distribuicoes` · `02-dominio-afixo` · `03-overlay-excecoes` · `04-colunas-reais`.

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2354-spec-bin-motor/run.py
```

## Escopo

Dirty (motor + medição). NÃO toca `src/tcf`. Dados: `Z:/tcf-data/interim/*.db`.
