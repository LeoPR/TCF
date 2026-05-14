# Indice incremental de padroes — abstracao

**Data**: 2026-05-13
**Tipo**: nota teorica (abstracao do mecanismo, implementacao depois)
**Vem de**: [`buffer-e-refragmentacao.md`](buffer-e-refragmentacao.md)
discussao sobre trade-off entre buffer pequeno (rapido, possivelmente
sub-otimo) e batch (otimo, custoso em volume grande).
**Conecta com**: Patricia tree (presente em M0 e Mobsolete) ja' faz
algo similar para strings — abstracao aqui generaliza pra sequencias
de refs e outras estruturas.
**Status**: registrada como **abstracao** — a forma de implementar
fica pra revisita depois. Nao bloqueia M4.C1.

## Tese central (do user)

Decidir entre combinacoes de padroes exige visualizar varios casos.
O caso otimo (batch sobre tudo pronto) e' custoso em volume grande.

Hipotese: com mecanismo de **acumulo + reavaliacao** (em uma linha
ou N linhas) + algoritmo de armazenamento em **grafo/arvore
inteligente**, da' pra ficar compacto e rapido de calcular/buscar.
Quase **indexacao de memoria** estilo banco de dados:

- vai armazenando
- um processo de index vai organizando (ou o proprio armazenamento
  ja' indexa junto)
- assim resolve buscas/comparacoes sem custo cubico

## Por que isso importa para M4.C2/C3

A nota anterior ([`buffer-e-refragmentacao.md`](buffer-e-refragmentacao.md))
mapeou 4 estrategias de buffer:
- 0/1 (online), medio (K linhas), batch (tudo), hibrido (online +
  refrag)

A escolha entre elas e' **trade-off de custo computacional vs
compressao**. Esta nota diz: **se a estrutura de armazenamento for
boa, o custo computacional cai muito** — quase elimina o trade-off.

Concretamente, em M4.C3 (online + refragmentacao), o decisor
precisa:
- Saber quais runs ja' viu (com contagem)
- Detectar quando novo padrao "supera" padrao ja' decidido
- Saber custo de refragmentar vs manter

Se isso for feito por scan linear sobre lista de runs vistos, custo
e' O(N²) ou pior. Se for indexado em estrutura tipo Patricia/trie,
custo cai para O(K log N) ou similar.

## Onde ja' temos parte disso

Patricia tree (implementada em M0 — `2026-05-10-02-patricia-nomes/`
em diante; refinada em Mobsolete em `2026-05-20-hierarquia-profunda/`)
ja' faz indexacao incremental **de strings**. Generalizar pra
**sequencias de refs** e' o passo natural.

Conexoes especificas:
- Patricia de strings: chars → galhos
- Patricia de sequencias de refs: idx → galhos
- Detector M2.A: ja' faz contagem (Counter) mas sem indexacao
- Detector M4.C que vamos fazer: pode usar mesma ideia

## Decisao para M4.C1 (proximo passo concreto)

Versao **batch sem estrutura sofisticada** — primeira iteracao:

- Roda tudo
- Coleta runs em dict simples (Counter)
- Greedy: ordena por net, seleciona, repete
- Custo computacional: O(N · L) onde L = numero medio de runs

**Suficiente para N pequeno (D1-D4 tem 12 linhas).** Para N grande
do prototipo, voltar a' esta nota e implementar com estrutura
indexada.

## Quando revisitar

- Apos M4.C1 medir resultado: se proximo passo for M4.C2 (online),
  ja' precisa indexacao basica
- Em M4.C3 (refragmentacao): indexacao se torna critica
- No prototipo: ANTES de escalar para datasets grandes

## Resumido em 1 linha

"Forma abstrata: armazenar+indexar incrementalmente em estrutura
tipo Patricia generalizada — barato em escala, fica pra otimizar
quando necessario."
