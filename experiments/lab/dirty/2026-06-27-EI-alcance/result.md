# EI global — medição de ALCANCE (lab read-only) [probatório]

**Data**: 2026-06-27. **Tipo**: experimento (gate read-only). Hipótese-mãe:
[hipotese-escape-invertido-EI.md](../../notas/hipotese-escape-invertido-EI.md).
Pergunta do owner: a estrutura "ideal" (flip global) **tem alcance**? Se tiver, desmontar e
**testar em estágios** a melhor forma de embutir. Mesmo com a hipótese de não ser ideal.

## Setup
Pós-filtro CEGO sobre o output single-col (`encode(list)` → body órfão): remove todo
`\`-antes-de-dígito (escape literal), prepende header `#TCF.8 EI`. Mede ganho **textual** e
**sob brotli**, em vários formatos digit-heavy (N=1000 realistas + colunas sintéticas
D11/D13/D14/D16). `safe` = o re-add ingênuo (`\` antes de todo digit-run) reconstrói o output
(teste de reversibilidade do filtro cego). Script: [medir_alcance.py](medir_alcance.py).

## Resultado
```
coluna                               n    esc  safe  txt-gain brotli-gain
cpf-regiao (aleatorio)            1000   3984     -     21.0%      -19.4%
id-num-9 (aleatorio)              1000    500     -      4.1%       -2.7%
id-num-16 (aleatorio)             1000    500     -      2.6%        0.0%
data (aleatoria)                  1000   1843     -     14.4%        6.0%
data (sequencial)                 1000     30     -      0.6%       -5.2%
telefone (aleatorio)              1000   2482     -     14.9%        9.4%
nfe-seq (formatado-seq)           1000      8     -     -3.2%       -3.0%
decimal (aleatorio)               1000   1986     -     18.1%       -6.5%
D11*-datetime (12 cols)             ~13  10-28    -   0-10.7%   -1.6..-27.6%
D13-cpf                             15     32     -     10.7%       -3.1%
D14-uuid                            12     66     -     13.3%        9.2%
D16a/b/c-ids (compressiveis)        13    1-6     -  -81.8..-10.5%  -60..-12%
```

## Achados

### (1) O filtro CEGO não faz round-trip — `safe` = falso em TODAS
O output mistura **escape-de-literal** (`\526`) com **dígitos estruturais** sem `\` (refs do
OBAT, contadores `*N` do seq-RLE). O strip remove só os escapes (correto: a regex `\<dígito>`
só pega literal); mas o re-add cego re-escaparia os estruturais → quebra. **Consequência: a
estrutura "ideal" (flip global cego) NÃO é um pós-filtro válido — ela já EXIGE ser embutida
no encoder, onde se sabe o que é literal vs estrutural.** O `txt-gain` medido é o ganho REAL
do strip (vale como teto), mas a reversibilidade precisa do encoder.

### (2) Alcance TEXTUAL: bom, mas só em coluna incompressível
- **Random/incompressível** (CPF 21%, decimal 18%, telefone 15%, data-rand 14%, uuid 13%):
  escapes dominam → ganho real. É o nicho do EI.
- **Estruturado/compressível** (data-seq 0.6%, nfe-seq −3.2%, ids D16 −10..−82%): o
  pipeline (OBAT/cadence/seq-RLE) já comprimiu → quase sem escapes → o header (10B) custa
  mais que os poucos `\` salvos → EI fica **net-negativo** mesmo textual.

### (3) Sob brotli: evapora ou INVERTE
CPF **−19.4%**, decimal −6.5%, maioria negativa; só telefone/data-rand/uuid levemente
positivos. Os `\` dão ao brotli um padrão de alinhamento regular (`\NNN.\NNN.`); removê-los
deixa o stream **menos** modelável → brotli pior. **EI não ajuda o regime brotli; costuma
prejudicar.** (Confirma o anti-incidente 2026-05-21: micro-opt textual some/reverte sob brotli.)

## Veredito de alcance: ESTREITO
A estrutura "ideal" (flip global) **não tem alcance amplo**:
1. O filtro cego nem round-trip faz → tem de ser **estágio dentro do encoder**.
2. Ganho só em **coluna incompressível** (random digit) e **só no regime textual/lazy**.
3. **Falha o gate "sob brotli"** — para consumidor comprimido, EI é neutro-a-negativo.

EI é uma otimização de **nicho textual** (alinhada à filosofia inspecionável do TCF), não um
ganho transversal. Promissor SÓ se o caso de uso for textual/lazy puro sobre colunas random
digit-heavy.

## Estágios (se/quando voltar — estudo deferido)
- **Estágio 0 (este lab)**: filtro cego → mede teto textual; revela não-round-trip + brotli-neg.
- **Estágio 1**: flip global **dentro do encoder** (sabe literal vs estrutural) → round-trip
  limpo + header flag. Regime textual só.
- **Estágio 2**: **serializado** (marcador inverte por linha/sequência) → só onde paga
  (gating por densidade de escape da coluna).
- **Estágio 3**: **preditivo** (decide pelo column-features antes de emitir).
Dado (2)+(3), mesmo o Estágio 1 é questionável fora do nicho textual. **Deferido.**

## Decisão
**Encostar o EI** (registrado: nicho textual, brotli-negativo, exige encoder-staging). Seguir
pro **GDICT B2** (cross-dict — único com ganho real-world JÁ medido, −19.3% SNAP). Se um caso
de uso textual/lazy-puro sobre random-digit aparecer, retomar pelo Estágio 1.
