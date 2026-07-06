# Conclusão — colchetes no meta (P5) [probatório]

Peça 5 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Números/estrutura: `artifacts/` (`python run.py`).

- **Funciona e é a construção mais enxuta**: a hierarquia vai **dentro do meta**, em colchetes
  (`[nome:9,telefones[tel]]`); `M`/`N` e **array-vs-objeto** são **deduzidos** (várias colunas ⇒ M;
  colchetes ⇒ N; nº de linhas dos filhos ⇒ array/objeto). **Decoda S4 e S6** (RT OK). S4 = 68B.
- **A hierarquia é opt-in**: só entra se for pra **reconstruir o JSON**; sem colchetes é multi-col plano.
  É a resposta ao "só mudar a semântica SE for pra json reconstruído".
- **A dedução "repetir vem dos filhos"**: array não precisa de flag — o próprio nº de linhas da coluna-
  filho revela 1:N. Liga com a peça 1 (a multiplicidade ×N é conservada; aqui ela vive na contagem de linhas).
- **Ambiguidades restantes** (a refinar com marca MÍNIMA só onde precisa): grupo de 1 linha (objeto vs
  array-de-1); grupo só-subgrupos; nome de coluna repetido; tipos. Ver README.

**Próximo**: escolher entre P3 (blocos+linking), P4 (multi-col+N+#H) e **P5 (colchetes, deduções)** — P5
é a mais próxima de "compacto e implícito". Depois: marca mínima p/ as ambiguidades + tipos, e então
pensar welding. Recomendo seguir com **P5** como base.
