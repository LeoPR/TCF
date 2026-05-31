# Revisao F2 — perspectiva matematica (escala e forma)

Esta nota substitui [conclusoes_F2.md](conclusoes_F2.md) na leitura
matematica. A anterior reportou "vencedores" por dimensao em
dataset minusculo — pratica que nao escala. Aqui ancora em
**complexidade, proporcao e regime**, nao em microbytes.

## Artefatos do dirty lab que invalidam comparacoes absolutas

Antes de qualquer leitura de F2, registrar:

1. **TCFs tem `[`/`]` delimitadores de body** — vestigio de output
   de array Python. ~5 bytes/arquivo de overhead. Em comparacao
   relativa entre micros nao distorce (todos pagam igual). Em
   numeros absolutos infla ~5% nos canonicos pequenos.
2. **Nao ha cabecalhos formais** (versao, nome de coluna, metadata
   de algoritmo). Em formato real teria mais bytes fixos.
3. **Datasets sao 4 x 12 strings ~15 chars cada** — escala minuscula.
   Diferencas de 1-10 bytes nao tem significancia estatistica nem
   teorica.

Portanto, qualquer leitura de F2 em bytes absolutos serve apenas
para **ilustrar regime**, nunca para concluir "X domina Y".

## Leitura matematica: cada micro como funcao de codificacao

Cada sintaxe e' uma transformacao linear sobre os tokens raw do
exp 16. Custo por unidade da condicao que a sintaxe ataca:

| Micro | Condicao atacada | Custo por unidade | Funcao de eficiencia |
|---|---|---|---|
| M1.A | char ambiguo no literal | +1 byte (`\X`) por char | constante 2× |
| M1.A' | seq K digitos no literal | +1 byte (`\<seq>`) por seq | (K+1)/K → 1 para K grande |
| M1.B | bloco com ambiguo | +2 bytes (aspas) por bloco | constante 2 bytes/bloco |
| M1.E | K refs consecutivas sequencial | ~4 chars (`a..b`) substituindo (2K-1) | 4/(2K-1) → 0 para K grande |
| M1.C | literal puro-digit start-of-line | -1 byte (sem `\`) por ocorrencia | 1 byte fixo |
| M1.D | ref (qualquer) | 3-6 chars (`e:a-b`) vs 1-2 (idx) | constante pior, +2-4 bytes/ref |

**Cada uma tem regime de eficiencia bem-definido pelo tamanho K
do padrao atacado.** A interacao entre essas funcoes determina o
custo total.

## Comportamento sob escala (extrapolacao teorica)

Seja n = numero de strings, m = media de chars/string, k = grau de
compartilhamento (% strings em "familia" com pref/suf comum).

**Custo de literais ancestrais** (que toda sintaxe paga):
- O(n) literais novos em pior caso
- Algumas familias: O(log n) literais (compressao Patricia-style)

**Custo de marcacao por micro** (fator multiplicador):
- M1.A: O(chars_ambiguos_total) = O(n·m·p_amb) onde p_amb e' freq
  de char ambiguo
- M1.A': O(n·m·p_seq) onde p_seq e' freq de seq digit ≥ 2
- M1.E: O(n·R/K) onde R = refs total, K = tamanho medio de
  sequencia de refs consecutivas
- M1.D: O(n·R) — independente de K (cada ref e' fixa)

**Comportamento em N → ∞:**

- M1.A: cresce linearmente com produto (n·m·p_amb). Escala
  proporcional a chars-ambiguos no dataset.
- M1.E: cresce linearmente com refs, mas FATOR 1/K. Em familias
  bem ordenadas (K grande), assintotica e' melhor.
- M1.D: cresce linearmente com refs, FATOR fixo. Pior assintotica
  que M1.E sempre que K > 2.

**Conclusao matematica (sem precisar de medicao):** M1.E domina
M1.D em assintotica para qualquer dataset com refs consecutivas
(que e' o caso geral do algoritmo exp 16 ao detectar pref/suf
contiguos). Verificado empiricamente nos canonicos (delta cresce
com regime).

## Comportamento sob gzip — analise teorica

gzip e' essencialmente LZ77 + Huffman. Sua eficiencia depende de
REPETICAO de subsequencias no texto. Cada micro produz
caracteristicas diferentes:

- **M1.A** produz refs verbosas (`,3,11,5,6` repetidas N vezes em
  linhas similares). Alta repeticao textual → gzip aproveita.
- **M1.E** comprime refs em range — restou pouca repeticao textual.
  gzip tem menos material.
- **M1.C** mesmo padrao de M1.E (poucas repeticoes para gzip).

Razao gzip observada (gzip/utf8) nos canonicos:
- M1.A: 0.612 - 0.760
- M1.E: 0.689 - 0.822
- Diferenca consistente ~7 pontos % a favor de M1.A em razao.

**Interpretacao teorica:** **agrupamento sintatico interno (M1.E)
e gzip externo competem pelo mesmo recurso — redundancia**. Quanto
mais o formato interno ja' agrupou, menos sobra para o compressor
externo.

**Implicacao escalavel:** em N → ∞, o ponto de equilibrio entre
"formato compactado" + gzip vs "formato verboso" + gzip depende
de:
- Tamanho do dicionario gzip (janela 32KB)
- Variedade de padroes (entropia)
- Frequencia de repeticao das refs verbosas

**Hipotese a testar em escala**: para N pequeno e familias
homogeneas, M1.A + gzip pode bater M1.E + gzip. Para N grande e
diversidade alta, M1.E + gzip tende a vencer (gzip nao escala
indefinidamente). **Precisa medir em N >= 10000 para confirmar.**

## Comportamento de tempo — analise teorica

A maior parte do tempo dos micros A/A'/B/E/C e' gasto em
`_coletar_quebras` que e' O(n·m) por dataset. Esse custo e' fixo
para o dataset, independente da sintaxe.

M1.D NAO chama `_coletar_quebras` — itera tokens raw diretamente.
Por isso e' 3-4x mais rapido em encode.

**Em escala N → ∞**: `_coletar_quebras` e' O(n·m). M1.D continua
O(n). **Diferenca de tempo cresce com N**, nao com m. M1.D tende
a ser dominante em tempo conforme N cresce.

## O que NAO foi testado (faltas teoricas)

Lista deliberada de hipoteses ainda nao exploradas no dirty lab:

1. **Redundancia entre linhas** (Camada 2 — aliases de tupla de
   refs). Identificada em
   [revisao-critica-M1E-output.md](revisao-critica-M1E-output.md).
   Nao implementado.
2. **Slice central real** (extende algoritmo exp 16 com
   TokRefSlice). Nao implementado. M1.D simplificado nao explora
   isso.
3. **Compressao binaria/alfabeto alternativo** — fora do escopo
   de marcacao textual.
4. **Header/metadata estrutural** — formato sem cabecalho atual.
5. **Multipla coluna** — algoritmo trata 1 coluna isolada. Em
   tabular real ha N colunas com correlacao.
6. **Decode parcial / aleatorio** — atualmente decode e' linear
   O(n). Acesso a linha k requer decodificar 1..k-1.

## Decisao: o que selecionar para prototipo

Em vez de "vencedor", definir candidatos por **regime de uso**:

### Candidato A: M1.E + escape escopo (M1.A' herdado)

**Quando usa**: dados tabulares com familias de strings, valor
representativo para casos reais (URLs, emails, paths).

**Justificativa matematica**: range em refs sequenciais tem
funcao de eficiencia 4/(2K-1) → 0 conforme K cresce. Em escala,
e' o que mais escala bem.

**Tradeoffs aceitos**: decoder stateful (modo escape escopo +
modo range), gzip aproveita menos, tempo encode maior.

### Candidato B: M1.A puro

**Quando usa**: dados onde gzip ja' faz boa parte do trabalho
(transito em rede), simplicidade importa, decoder stateless e'
requisito.

**Justificativa matematica**: razao gzip ~0.65 vs ~0.75 do M1.E.
Em transit comprimido pode pagar custo de marcacao verbosa.

**Tradeoff aceito**: formato em disco e' maior que M1.E.

### Nao selecionados (justificativa para fechar exploracao no dirty):

- **M1.A'**: dominada por M1.E em todas as dimensoes (M1.E herdou
  M1.A' e adiciona range)
- **M1.B**: custo fixo de aspas (~2 bytes/bloco) sem ganho
  proporcional. So' vence em casos muito especificos
  (D3 bz2 isolado)
- **M1.C**: empate com M1.E em ref-context; ganho marginal em
  start-of-line. Combinavel mas nao justifica exploracao
  isolada
- **M1.D**: dominada estruturalmente por M1.E enquanto algoritmo
  base for exp 16 (refs sao consecutivas → range mais barato que
  slice). So' competitivo se modificar algoritmo (M2 com
  TokRefSlice real).

## Recomendacao para proximo passo

**Fechar M1 com a leitura:**

> O dirty lab M1 explorou 6 dimensoes semanticas de marcacao de
> ambiguidade e redundancia local. Tres dimensoes (escape escopo,
> range, sumida) sao matematicamente uteis. As outras tres
> (escape pontual, quote em grupo, slice) ou sao dominadas ou
> tem regime de uso estreito. Para prototipo, **M1.E (range +
> escape escopo)** combina ganhos ortogonais e tem comportamento
> assintotico previsivel.

**Antes de prototipo, considerar 1 experimento paralelo:**

Talvez valha um teste rapido de **aliases de tupla** (M2 macro) no
proprio dirty lab — ataca camada 2 (redundancia entre linhas) que
ficou nao tocada. Custo: 1-2 dias. Beneficio: confirmar/refutar
hipotese antes de gastar no prototipo.

Outras hipoteses (slice central real, multi-coluna, decode
aleatorio) sao melhor exploradas em prototipo com escala real.

## Decisao do user

- (a) Fechar M1 agora e ir para prototipo com M1.E base
- (b) Fechar M1 e fazer 1 macro rapido M2 (aliases de tupla) antes
  do prototipo
- (c) Outro caminho

## Limpeza pendente antes do prototipo

- Remover `[`/`]` delimitadores de body (sem funcao real)
- Adicionar cabecalho formal (versao, coluna, metadata)
- Definir formato canonico de linha (newline policy, encoding)
- Normalizar separadores (talvez `*` vire algo mais elegante)
