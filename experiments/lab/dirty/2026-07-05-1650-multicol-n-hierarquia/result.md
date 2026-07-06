# Conclusão — modelo multi-col + `N` [probatório]

Peça 4 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Artefatos: `artifacts/` (`python run.py`).

- **A via mais simples funciona**: 1 multi-col TCF + flag `N` no shebang + 1 linha `#H` de hierarquia →
  **decoda S4 e S6** (RT OK, `04-decode-*`). É "a estrutura que já temos, com um complemento barato".
- **Por que é mais simples que a peça 3**: sem blocos `@block` separados nem header de arestas; as
  colunas já vêm em ordem no multi-col, e o `#H` só as **reagrupa** na árvore. Nomes obrigatórios ficam
  no meta (referência principal), como o owner pediu.
- **Trade honesto**: colunas num blob só (menos buscáveis independentemente que os blocos da P3), e há
  **redundância de nomes** (#H + meta) — o próprio owner apontou a compactação: **1ª coluna do meta = o
  indicador de hierarquia** (fundir #H no meta), ou #H por **posição** em vez de nome.
- **Limite** (igual à P3): array-dentro-de-array e N raízes precisam de **link posicional** (peça 5).

**Próximo**: escolher entre P3 (blocos+linking) e P4 (multi-col+N) — ou um híbrido — e então compactar +
tipos. Recomendo levar a **compactação da P4** (fundir #H no meta) porque é a mais barata e a mais
próxima do formato atual.
