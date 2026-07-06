# 2026-07-05 18:40 — ESTUDO: notações de agrupamento (qual a mais minimalista) [probatório]

**Peça 6** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). Auto-contido: `notationlib.py`
(nem usa `tcf` — é só a camada de header). `python run.py` regenera. **Foco: o ESTUDO da notação, não os colchetes.**

## Pergunta

Qual a forma **mais minimalista** de agrupar colunas numa árvore, num cabeçalho linear? O owner levantou
três famílias: **símbolo entre elementos**, **contagem inicial**, **start/end**. Aqui elas são comparadas
(encode + parse-de-volta + bytes), sem casar com nenhuma.

## As candidatas (todas RT a topologia — `artifacts/`)

| notação | ideia | S4 | S6 |
|---|---|---|---|
| **S · start/end** | `nome[filhos]` (colchetes) | **19B** | **53B** |
| **A · descend/ascend** | `nome>filhos<` (símbolos entre elementos) | **19B** | **53B** |
| **C · contagem** | `nome*N f1 f2 …` (aridade por nó interno) | 20B | 56B |
| **D · profundidade** | `nome:1 filho:2` (nível por nó) | 24B | 68B |

S6 (`01-comparacao-S6.txt`):
```
S  nome,endereco[rua,cidade,geo[lat,lon]],telefones[tel]
A  nome,endereco>rua,cidade,geo>lat,lon<<,telefones>tel<
C  nome endereco*3 rua cidade geo*2 lat lon telefones*1 tel
D  nome:1 endereco:1 rua:2 cidade:2 geo:2 lat:3 lon:3 telefones:1 tel:2
```

## Achados

1. **Todas reconstroem a árvore** (RT OK). Cada uma é um encoding válido da mesma topologia+nomes.
2. **Bytes quase não mudam**, e nesta escala o **delimitador (S/A) é o menor** — `[`/`]` (ou `>`/`<`) são
   1 char cada. **C (contagem)** empata quase (marca só nós internos, mas o `*N` + espaços custam ~o
   mesmo). **D (profundidade) é o pior**: marca TODO nó, inclusive as 5 folhas (1 número por coluna).
3. **A escolha não se decide por bytes** (diferença de ~3–15B em <70B) — decide-se por **parse/stream**:
   - S/A: precisa casar delimitadores (pilha), mas é 1 passada.
   - C: 1 passada pura (a contagem diz quando parar — ótimo pra streaming/append).
   - D: 1 passada com pilha por nível; marca redundante em folha.
4. **Teoria (o achado que importa)**: uma lista linear de irmãos + separador **NÃO** reconstrói árvore.
   Precisa de **UM portador de forma**: `{delimitador casado}` OU `{contagem/aridade}` OU `{profundidade}`.
   O "símbolo entre elementos" **só** resolve o nesting **se** for um desses (ex.: `>`/`<` = delimitador).
   Um separador de irmãos sozinho dá só a lista plana.
5. **Ortogonal**: array-vs-objeto continua **deduzido do nº de linhas** (peça 5); e os **sizes/dados** não
   entram na notação — a comparação acima é só a camada de agrupamento.

## Leitura pro projeto

- **Não há vencedor por bytes** nesta escala; qualquer um dos três portadores serve. A decisão real é
  **parse/stream** (C é a mais streamável; S/A a mais familiar) e a forma dos dados (árvores muito
  profundas favorecem contagem/profundidade sobre delimitador só na legibilidade, não em bytes).
- Recomendo **não** cravar a sintaxe agora: fixar o PRINCÍPIO (1 portador de forma, deduções de peça 5,
  hierarquia opt-in) e escolher o glifo na hora do welding.

## Cross-links

Complementa o survey de linking da [peça 3](../2026-07-05-1608-linking-pai-filho-cabecalho/result.md)
(adjacency/path/nested-set/parens) — lá era ligar BLOCOS; aqui é a topologia num header linear.
Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
