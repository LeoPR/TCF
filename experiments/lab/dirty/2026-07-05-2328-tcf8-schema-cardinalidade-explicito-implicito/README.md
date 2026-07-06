# 2026-07-05 23:28 — TCF.8 + semântica de cardinalidade/hierarquia: explícito → mínimo [probatório]

**Peça 9** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) — **ponte** com o
header-minimal ([2026-07-01](../2026-07-01-header-minimal/result.md)). Auto-contido: `schemalib.py` + `tcf`
(**não toca `src/`**). `python run.py` regenera.

## A pergunta (do owner)

Incluir a **semântica de cardinalidade/hierarquia** no header TCF.8 — vale? (cardinalidade ≈ hierarquia,
são quase a mesma coisa: 1:N = duais, medido nas peças 1/7). **Metodologia**: escrever a linguagem
semântica **COMPLETA** (todos os itens explícitos), depois ver **o que dá pra tirar** (implícito). A
linguagem é a mesma; implícito/explícito é uma camada de cima.

## O que foi feito

1. **Header EXPLÍCITO** (`01-header-explicito-*.txt`): a linguagem com TODOS os itens — flag M/N, e por nó
   `kind`/`rows`/`parent`/`card`(cardinalidade), e por coluna `type`/`marker`/`size`/`in`. Ex. (S6):
   ```
   #TCF.8 M N
   @grp $root kind=object rows=1 parent=- card=-
   @col nome type=str marker=! size=8 in=$root
   @grp endereco kind=object rows=1 parent=$root card=1:1
   ...
   @grp telefones kind=array rows=2 parent=$root card=1:N
   @col tel type=str marker=! size=30 in=telefones
   ```
2. **Dedução** (`00-deducao-e-bytes.txt`): o que sai (implícito) vs o que é IRREDUTÍVEL.
3. **Header MÍNIMO** (`02-header-minimo-*.tcf.txt`): dedução aplicada = **o colchete da P5**.
4. **Decode** (`03-decode-rt-*.txt`): o mínimo **reconstrói o JSON** — a dedução não perde informação.

## Achado — a forma mínima da linguagem completa CONVERGE pra P5

| item | deduzível? | de quê |
|---|---|---|
| magic `#TCF.8` | **NÃO** | roteamento/versão |
| flag M / flag N | SIM | ≥2 colunas / aninhamento presente (P5/P6) |
| **hierarquia (arestas pai→filho)** | **NÃO*** | é o SCHEMA; *derivável se pré-acordado (O-FMT-14) |
| cardinalidade / kind / rows | SIM | nº de linhas dos filhos (P7): 1→obj, N→array |
| type (str/num) | parcial | default str; senão `:tipo` |
| nomes | parcial | drop_names se anônimo |
| marker (`!`/`@`/`%`) / size | NÃO / parcial | decode precisa / última-sem-size |

**Bytes (só header)**: S6 explícito **508B → mínimo 74B** (15%), RT OK. S4 222B → 31B. **IRREDUTÍVEL**:
magic + arestas de hierarquia + markers + sizes. Tudo mais é implícito.

## Resposta à pergunta

**SIM** — incluir a semântica de cardinalidade/hierarquia no TCF.8 é sólido, e o **custo no formato
transmitido é ZERO**: fica **implícito/deduzido** (o mínimo = colchete P5, que já provamos). Vira
**explícito** só quando o consumidor quer o schema, ou **derivável/pré-acordado** (O-FMT-14). **Cardinalidade
e hierarquia são a mesma camada** — a "linguagem de schema" que o header-minimal precisava (o contrato) É
essa. Fecha o círculo: header-minimal (frontier = header derivável) + hierárquico (a linguagem) = o mesmo.

## Estado

- **É**: a linguagem semântica explícita + a dedução + a convergência pro mínimo (P5), medido + RT.
- **Será** (protótipo formal, exige aprovação — toca formato/src): TCF.8 opt-in que carrega a hierarquia
  (arestas irredutíveis) + deduz o resto; e o modo derivável (O-FMT-14) quando o schema é pré-acordado.

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
