# docs/theory: teoria e hipóteses do TCF

> **Reset 2026-05-17**: o conteudo anterior de `docs/theory/`
> (architecture, components, methodology, research-lines) descrevia
> v0.4/v0.5 e foi arquivado em `docs/archive/theory_*_v05/`. Em seu
> lugar, notas teoricas e hipoteses do v0.6 (antes em
> `experiments/lab/dirty/notas/`) foram movidas pra ca' em 2026-05-17.
>
> **Agrupamento 2026-08-30**: as notas estavam soltas na raiz da pasta, sem dar pra saber o
> que andava com o que. Agora cada assunto tem a sua pasta, e a raiz guarda so' este indice
> e o registry de hipoteses. A tabela [onde foi parar](#onde-foi-parar) traduz os caminhos
> antigos, porque ADR aceito nao e' editado e continua apontando pro lugar de antes.

## Onde esta a teoria canonica

**Algoritmos** (as camadas do TCF, fora desta pasta):
- [`../algorithms/OBAT.md`](../algorithms/OBAT.md): Online Bidirectional Affix Tokenizer (camada 1)
- [`../algorithms/HCC.md`](../algorithms/HCC.md): Hierarchical Compositional Coding (camada 2)
- [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md): formato e posicionamento
- [`../algorithms/output-convention.md`](../algorithms/output-convention.md): convencao de output

**Narrativa do desenvolvimento**: [`historia-dirty-lab.md`](../../experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md),
a historia M0-M14 do dirty lab.

## As pastas

| pasta | o assunto | notas |
|---|---|---|
| [`comparacao/`](comparacao/) | o que o nucleo compara, e como | 3 |
| [`desempenho/`](desempenho/) | os vetores alem de bytes: memoria, latencia, nucleo compilado | 3 |
| [`estrutura/`](estrutura/) | padroes estruturais e estudos de estrutura de dados | 3 |
| [`marcadores/`](marcadores/) | a sintaxe e o custo dos marcadores no wire | 4 |
| [`strategies/`](strategies/) | o mapa de estrategias v1.0, segmentado por subsistema | 9 |
| [`tipos-e-naturezas/`](tipos-e-naturezas/) | pre-tx pela natureza do dado | 5 |
| [`tres-blocos/`](tres-blocos/) | presenca, nulo e ausencia: a particao e o vocabulario | 6 |

Na raiz ficam so' este indice e [`roadmap-hipoteses.md`](roadmap-hipoteses.md), o registry
das hipoteses futuras ordenadas por proximidade.

---

## comparacao/

O eixo do que significa duas coisas serem parecidas.

- [duas-similaridades-igualdade-e-proximidade.md](comparacao/duas-similaridades-igualdade-e-proximidade.md):
  **ATUAL (2026-08-09)**. O nucleo captura DUAS similaridades (igualdade = dedup `^N`/bN/dict;
  proximidade = seq-RLE/periodico/delta) e elas **nao competem no mesmo `min()`**: a aritmetica
  morre na linha `k`, porque a primeira repeticao aciona o dedup. Coluna ciclica `01..12` custa
  423 B contra 20 B da mesma aritmetica sem repetir. Reenquadra o papel dos SPECS, que escolhem
  um DOMINIO onde a aritmetica sobrevive em vez de "adicionar semantica". Tudo `.9`
- [comparacao-modular-camadas.md](comparacao/comparacao-modular-camadas.md):
  comparacao modular (delta, estrutural, aproximado) ortogonal ao TCF-CORE
- [2026-05-11-comparacoes-nao-literais.md](comparacao/2026-05-11-comparacoes-nao-literais.md):
  precursor da Estrategia 1

## desempenho/

Compressao nao e' o unico eixo, e este grupo guarda os outros.

- [perspectiva-triplice-e-pre-tx.md](desempenho/perspectiva-triplice-e-pre-tx.md):
  **ATUAL (2026-05-17)**. A perspectiva triplice (compressao, memoria, latencia) e a analise
  critica das 3 estrategias de evolucao. Ancorado no [ADR-0002](../adr/0002-vertice-triplice-restricao.md)
- [vetores-de-comparacao-alem-de-bytes.md](desempenho/vetores-de-comparacao-alem-de-bytes.md):
  velocidade, memoria, streaming, latencia
- [h-perf-06-exploration.md](desempenho/h-perf-06-exploration.md):
  estudo do nucleo compilado (Cython, Rust). A hipotese original foi **desconfirmada** por
  profiling real: o gargalo e' o `_detect_compositions` do HCC, nao o lcp/lcs

## estrutura/

Estudos de estrutura, do no' template ao indice de padroes.

- [no-funcional-marca-e-troca.md](estrutura/no-funcional-marca-e-troca.md):
  template node com slot (caso D9). Nao implementado, registrado para estudo
- [patricia-trie-exploration.md](estrutura/patricia-trie-exploration.md):
  viabilidade da Patricia trie no OBAT (H-TH-02). Decisao: v1.0 mantem hash trigrama, a
  Patricia fica como candidata v2.0
- [schema-gadget-design.md](estrutura/schema-gadget-design.md):
  design do gadget de schema e qualidade (T-RECOVER-SCHEMA-MULTI-TABLE)

## marcadores/

A sintaxe do wire: o que cada marcador custa, e o que ele pode significar.

- [marcadores-multiplo-proposito.md](marcadores/marcadores-multiplo-proposito.md):
  o composicional `~` e `,`, que e' a fundacao do HCC
- [2026-05-11-marcadores-compactos.md](marcadores/2026-05-11-marcadores-compactos.md):
  marcadores compactos e inferidos
- [2026-05-11-custo-de-marcadores.md](marcadores/2026-05-11-custo-de-marcadores.md):
  o custo algebrico de marcadores, refs e indices
- [quebra-de-linha-como-marcador.md](marcadores/quebra-de-linha-como-marcador.md):
  quebras como marcadores deduziveis

## strategies/

O mapa de estrategias do v1.0. O monolito e a sua segmentacao agora moram juntos.

- [INDEX.md](strategies/INDEX.md): o indice das 118 estrategias, por camada do pipeline
- [strategies-map.md](strategies/strategies-map.md): o arquivo unico de origem, preservado

## tipos-e-naturezas/

O pre-tx pela natureza do dado, e o que a spec pode ou nao mandar.

- [data-natures-taxonomy.md](tipos-e-naturezas/data-natures-taxonomy.md):
  **2026-05-15**. A taxonomia das 8 naturezas comportamentais (incremental, templated,
  enumerated, checked, composite, hierarchical, lossy-recoverable, high-entropy), que
  operacionaliza a Estrategia 1.A
- [tipos-o-caminho-do-dado-ate-o-tcf.md](tipos-e-naturezas/tipos-o-caminho-do-dado-ate-o-tcf.md):
  o eixo do CAMINHO (as 9 fronteiras entre a fonte e o TCF), complementar ao eixo
  COMPORTAMENTAL da taxonomia
- [spec-orienta-nao-manda-triagem.md](tipos-e-naturezas/spec-orienta-nao-manda-triagem.md):
  **2026-08-09**. A triagem do que e' nucleo generico contra o que e' dica de spec, com o
  corpus ditando o default. Distribui os itens entre `.8`, `.9` e `2.0`
- [float-e-variantes-consolidado.md](tipos-e-naturezas/float-e-variantes-consolidado.md):
  o tipo `float` no `#TCF.8`: o que fecha, e as variantes que mexem na grafia (lossless) ou
  no valor (loss). O formato segue lossless-puro
- [2026-05-11-tipos-com-estrutura.md](tipos-e-naturezas/2026-05-11-tipos-com-estrutura.md):
  tipos estruturados (CPF, UUID, IP), precursor da Estrategia 1.A

## tres-blocos/

Presenca, nulo e ausencia. Por que o wire distingue tres estados por celula, e como se
pergunta por cada um.

- [INDEX.md](tres-blocos/INDEX.md): o mapa, mais o quickuse das cinco perguntas
- as notas cobrem a particao e as oito unioes, os termos firmados, o que nao serve,
  o lift duplo e o mimetismo com Mongo, Postgres, Arrow, polars e R

---

## Onde foi parar

O agrupamento de 2026-08-30 moveu 19 arquivos. A superficie viva foi reescrita; o **traco**
nao, porque ADR aceito nao e' editado e os labs sao append-only. Quem chegar por um ponteiro
antigo se encontra aqui:

| caminho antigo | agora em |
|---|---|
| `theory/2026-05-11-comparacoes-nao-literais.md` | `theory/comparacao/` |
| `theory/comparacao-modular-camadas.md` | `theory/comparacao/` |
| `theory/duas-similaridades-igualdade-e-proximidade.md` | `theory/comparacao/` |
| `theory/h-perf-06-exploration.md` | `theory/desempenho/` |
| `theory/perspectiva-triplice-e-pre-tx.md` | `theory/desempenho/` |
| `theory/vetores-de-comparacao-alem-de-bytes.md` | `theory/desempenho/` |
| `theory/no-funcional-marca-e-troca.md` | `theory/estrutura/` |
| `theory/patricia-trie-exploration.md` | `theory/estrutura/` |
| `theory/schema-gadget-design.md` | `theory/estrutura/` |
| `theory/2026-05-11-custo-de-marcadores.md` | `theory/marcadores/` |
| `theory/2026-05-11-marcadores-compactos.md` | `theory/marcadores/` |
| `theory/marcadores-multiplo-proposito.md` | `theory/marcadores/` |
| `theory/quebra-de-linha-como-marcador.md` | `theory/marcadores/` |
| `theory/strategies-map.md` | `theory/strategies/` |
| `theory/2026-05-11-tipos-com-estrutura.md` | `theory/tipos-e-naturezas/` |
| `theory/data-natures-taxonomy.md` | `theory/tipos-e-naturezas/` |
| `theory/float-e-variantes-consolidado.md` | `theory/tipos-e-naturezas/` |
| `theory/spec-orienta-nao-manda-triagem.md` | `theory/tipos-e-naturezas/` |
| `theory/tipos-o-caminho-do-dado-ate-o-tcf.md` | `theory/tipos-e-naturezas/` |

## Conceitos pendentes para reconectar

Identificados pelo user em 2026-05-17 (todos cobertos em
[perspectiva-triplice-e-pre-tx.md](desempenho/perspectiva-triplice-e-pre-tx.md)):

1. **Multi-coluna**: ~~TCF v0.6 atual e' single-column~~ → **welded em 0.7** (ADR-0011/0004; `#TCF.7 M`).
2. **Tipos de dados pre-filtro**: CPF, IP, datas calculaveis (ADR-0015, welded 0.7).
3. **Perspectiva triplice**: compressao + memoria + latencia.
4. **Slot pattern online**: resolve `17,??,5` em D9.

## Material historico v0.5

Anteriormente em `docs/theory/` mas v0.5-exclusivo, arquivado em:
- `../archive/theory_architecture_v05/`
- `../archive/theory_components_v05/`
- `../archive/theory_research_lines_v05/`
- `../archive/theory_methodology_v05/`

**Nao citar como evidencia viva para v0.6 sem re-validar.**
