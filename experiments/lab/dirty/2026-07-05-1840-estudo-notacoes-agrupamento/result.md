# Conclusão — notações de agrupamento [probatório]

Peça 6 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Números: `artifacts/` (`python run.py`).

- **O estudo, não os colchetes**: comparei 4 notações que encodam a MESMA árvore num header linear —
  start/end (`[]`), descend/ascend (`> <`), contagem (`nome*N`), profundidade (`nome:d`). **Todas RT a
  topologia** (S4 e S6).
- **Bytes quase empatam** e o delimitador (`[]` / `> <`) é o menor nesta escala (S6: 53 vs 56 vs 68).
  **A escolha não se decide por bytes** — decide-se por **parse/stream**: contagem é a mais streamável
  (1 passada pura), delimitador a mais familiar, profundidade marca folha à toa.
- **O achado que importa (teoria)**: pra reconstruir uma árvore num cabeçalho linear precisa de **UM
  portador de forma** — `{delimitador casado}` OU `{contagem/aridade}` OU `{profundidade}`. Separador de
  irmãos sozinho dá só lista plana. O "símbolo entre elementos" do owner **é** um portador **se** marcar
  descend/ascend (= delimitador).
- **Ortogonal**: array-vs-objeto vem do nº de linhas (peça 5); sizes/dados não entram na notação.

**Recomendação**: não cravar a sintaxe agora. Fixar o **princípio** (1 portador de forma + deduções da
peça 5 + hierarquia opt-in) e escolher o glifo no welding. Próximo do estudo: as **ambiguidades** (peça 5:
grupo de 1 linha, nomes repetidos, tipos) e o **link posicional** (peça 7) — que é o único que muda o
jogo (precisa de número, não só forma).
