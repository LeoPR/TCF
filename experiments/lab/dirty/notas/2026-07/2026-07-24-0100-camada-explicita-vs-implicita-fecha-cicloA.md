# Camada explícita vs implícita + tolerância-com-warning — fecha o Ciclo A [modelo / fechamento]

**Data**: 2026-07-24 01:00. Modelo articulado pelo owner, que reconcilia todo o estudo do cabeçalho e
guia o que vem: *"a camada explícita permanece sempre igual, ela guia a gente com o correto, e a
simplificação apenas mostra que o correto não precisa estar escrito no arquivo — desde que a dedução
não caia em ambiguidade"* + *"ser tolerante com warning sempre que possível"*.

## O modelo (duas camadas)

| camada | o que é | muda? |
|---|---|---|
| **EXPLÍCITA** | a grafia canônica, tudo escrito. É a fonte da verdade; guia a corretude. | **NUNCA** |
| **IMPLÍCITA** | dedução/simplificação POR CIMA. O correto não precisa estar escrito. | opcional |

**Regra de ouro**: toda forma implícita tem que **deduzir de volta, sem ambiguidade, para a forma
explícita**. A implicitude é uma *view* mais curta de algo que continua tendo uma forma completa.

**Onde há ambiguidade**: **tolerar com warning** (aceitar + avisar que não é canônico), **não**
fail-loud — sempre que possível. Fail-loud só quando aceitar corromperia o dado em silêncio. Precedente
no código: coluna anônima já emite `UserWarning` (`multi/core.py:327`); é o mesmo canal.

## Como isso fecha as questões pequenas do Ciclo A

Cada "simplificação" estudada é uma dedução da MESMA forma explícita — não uma forma nova:

- **Header**: a forma explícita é `#TCF.8 {nome}:{id}` (forma (1), já real, robusta — carrega tudo).
  As implícitas deduzem dela por EXCLUSÃO, sem ambiguidade porque o `{id}` vem de namespace FECHADO:
  - sem nome + tag primitiva → `#TCF.8{tag}` (forma (6)); a rota single-col é intuída por exclusão
    (não é `M`/`H`/espaço/`\n`).
  - tipo string → **órfão** (header 0 B): string é o default, deduzido por ausência de tag.
  - A ambiguidade que refuta (2)/(4) é justamente a que a regra proíbe: expor o índice 6 a um NOME
    (dado aberto) permite deduzir errado (nome `M` → multi-col). Por isso só (1)+(6) sobrevivem.

- **Vazio / LF** (lab `0033`): a forma explícita usa LF como TERMINADOR (é o que o `encode` já faz):
  `#TCF.8\n`→`[]` · `#TCF.8\n\n`→`['']` · `#TCF.8\n\n\n`→`['','']`. Hoje o decode é TOLERANTE e colapsa
  `#TCF.8\n` e `#TCF.8\n\n` em `['']` — não-canônico. Sob o modelo: manter tolerante MAS **avisar** que
  a grafia sem terminador é não-canônica; a grafia canônica (com terminador) é a que o encode emite.

- **Vazio dispensa a tag**: `[]` de bool = `[]` de int (zero elementos, nenhum tipo a preservar).
  `#TCF.8b\n` é legal porém redundante; a canônica é `#TCF.8\n` (sem tag). `#TCF.8b\n\n` = fail-loud
  (`''` não é `true`/`false`) — aqui aceitar corromperia, então é o caso de fail-loud legítimo.

## Consequência prática — o "pré-avaliador de apelidos" (owner 2026-07-24)

A implicitude **nunca precisa de código de decode novo por forma** — precisa de um passo que
**expande a forma implícita para a explícita** e delega o resto ao decode canônico. É barato e
mantém uma fonte-da-verdade única. Foi assim que o gate da tipagem fechou (lab `0006`): a tag expande
para o tipo; o corpo é o mesmo do explícito.

**Não é competição simplificado-vs-completo — é simplificado VIRA completo e segue.** Modelo do owner:

> *Toda versão tem uma forma completa; ela só precisa ser preenchida. O macete da parte implícita é
> que ela deduz o que DEVERIA estar completo; o resto do código segue a parte completa sempre, sem
> mutar nada — a gramática em si não muda, o que muda é um pré-avaliador de apelidos.*

- **Camada 1 (implícita)** = *pré-avaliador de apelidos*: um passe fino na BORDA que, ao ver uma forma
  curta, a **normaliza para a forma explícita completa** (preenche o que foi deduzido).
- **Camada 2+ (o resto)** = encode/decode canônicos, que **só veem a forma completa**, intocados.

**Analogia (owner)**: o contrato inicial padroniza "só nomes completos" para formalizar o padrão;
DEPOIS cria-se a camada de apelidos. O padrão fica na 2ª camada, mas **não muda a interpretação do
resto**. Isto **derruba o risco do weld #4** (single-col tipado): não se toca no core da gramática —
adiciona-se um normalizador `implícito → explícito` na entrada e um compactador `explícito → implícito`
opcional na saída. (Otimizações internas podem depois "curto-circuitar" as duas camadas por
performance, mas a MODULARIZAÇÃO limpa é essa.)

**Weld #1 (2026-07-24, FEITO)** é o primeiro tijolo dessa camada: `split_lf_body` passou a
tolerar-com-warning o corpo sem terminador canônico — o decode começou a *sinalizar* desvio da forma
explícita, sem mudar nenhum byte (aditivo, +13 linhas, suíte 861 verde, baselines intactos).

**Weld #2 (2026-07-24, FEITO)** — canonicidade do vazio: `[]` passou a ser expressa na forma FLAT
`#TCF.8\n` (7 B) em vez de fugir pro `.8H` `#D0` (11 B). Fronteira do vazio agora canônica:
`#TCF.8\n`→`[]` · `#TCF.8\n\n`→`['']` · `#TCF.8\n\n\n`→`['','']`. O `#D0` legado ainda é tolerado no
decode. Isolado (colunas vazias aninhadas usam `if cols[key] else ''`, não passam pelo top-level).
+22 linhas em encoder+decoder; 3 testes re-pinados (ADR-0024) + 1 root_kind ajustado; catálogo
regenerado; **suíte 861 verde, baselines byte-canônicos intactos** (D1-D9=1523B/D17a=300B/real=89616B).

## O que fica pendente de DECISÃO do owner (não é medição — é escolha)

1. **Adotar a convenção terminador** e tornar o decode *tolerante-com-warning* (hoje é tolerante-
   silencioso). Destrava `[]` na forma flat (7 B vs 11 B do `.8H#D0`) e restaura canonicidade.
2. **Namespace fechado de tags** (`b`/`n`/`s`/…) para habilitar a forma (6) — a whitelist que torna a
   dedução por exclusão segura.
3. **default do header**: manter `#TCF.8` sempre (owner: sim); remoção (órfão) exige parâmetro
   explícito. Hoje é o inverso — órfão é default.

Relaciona: [plano `.8`](../2026-06/tcf8-estrutura-plano.md) §S1 · labs
[`0006`](../../2026-07/2026-07-24/2026-07-24-0006-cicloA-formas-hipoteticas-resistencia/) ·
[`0033`](../../2026-07/2026-07-24/2026-07-24-0033-cicloA-vazio-canonicidade-LF/) ·
[`2330`](../../2026-07/2026-07-23/2026-07-23-2330-cicloA-cabecalho-tipo-nature-nome/) ·
[regra de implicitude `0259`](2026-07-23-0259-implicitude-singlecol-logica.md).
