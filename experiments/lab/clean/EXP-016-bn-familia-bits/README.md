# EXP-016 — família bN/bits: bateria sintética completa [probatório]

**Lab clean** que fecha o estudo da família **bN** (bits densos de domínio, ADR-0036) e da
**camada de borda de polaridade** (ADR-0035). Consolida o estudo dirty de 2026-07/08 numa
bateria **declarativa e auto-verificável**: cada caso diz o que espera **antes** de rodar, e
o lab **falha** quando não acontece.

```
python run.py     # regenera inputs/, outputs/ e report.md; exit 0 só se tudo fechar
```

Estado atual: **72 casos em 11 famílias, 0 falhas.** `src/tcf` **não é tocado**.

## Por que este lab existe

O estudo dirty produziu a mecânica; o que faltava era a **contraprova em regime**. Um lab
dirty responde *"funciona neste caso?"*; este responde *"funciona em toda a variedade que
sabemos construir, e o que exatamente acontece quando não ativa?"*. É a diferença entre
um número de terminal e um número gravado — a mesma cobrança que motivou o
[incidente dos 4 bugs](../../dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md).

## As cinco provas, por caso

| prova | o que garante | por que é separada |
|---|---|---|
| **RT estrito** | valor + tipo + sinal + comprimento, contra os dados **originais** | comparar contra o próprio decode é validação circular (lição do lab `2026-07-26-0038`, retratado) |
| **determinismo** | `encode` duas vezes → byte-idêntico | o FLOOR não pode depender de ordem de iteração |
| **nunca-pior** | o wire com bN **nunca** é maior que o wire sem bN | é a invariante da família: mecanismo novo entra como **candidato**, nunca como substituto |
| **correção ≠ bN** | o core sozinho **também** faz RT | o bN é opção de **tamanho**; se um dia ele for necessário pra correção, algo se acoplou errado |
| **o artefato é o wire** | o `.tcf` em disco lido em **binário** é byte-idêntico ao wire medido | pegou o modo texto do Windows traduzindo `\n` → CRLF: os `.tcf` gravados **não eram** o wire |

A quarta é a menos óbvia: ela impede que o bN vire dependência silenciosa. Se o core sozinho
parar de fazer RT num caso, o lab acusa mesmo com o bN funcionando perfeitamente.

A quinta nasceu de um defeito real deste lab. Os `.tcf` estavam saindo com `\r\n` — RT,
determinismo e bytes todos corretos, e mesmo assim **o arquivo publicado não era o que foi
medido**. Num lab probatório, o artefato mentir sobre a medição é o mesmo que não ter
medido; então a checagem virou prova.

## As 11 famílias

| família | o que estressa |
|---|---|
| **F1** bool/binário | o regime-alvo: `k=2`, o que originou o bN |
| **F2** null | o slot 0 pré-alocado — null convive com qualquer tag |
| **F3** bordas | `k=1`, `k=2`, `k=256`, `k=257` (o teto, `MAX_W=8`) |
| **F4** espaços | vazio, só-espaço, espaço à borda — o que o `strip` comeria |
| **F5** número | valores que **parecem** número e o corpo canônico escapa (`\0`, `\1`) |
| **F6** cabeçalho | canonicidade do header: zero à esquerda, hex maiúsculo, `0x`, sinal, `_` do PEP-515, dígito Unicode |
| **F7** escape | o `\` no domínio, o marcador `=` no domínio, escape do escape |
| **F8** tipos | int, float, `-0.0`, misto int/float, int grande — a rota **tipada** |
| **F9** unicode | acento, CJK, emoji, combining, RTL |
| **F10** bN×RLE | o corpo perfeitamente RLE-ável, onde o bN **deve perder** |
| **F11** fronteira | as larguras `w ∈ {1,2,4,8}` e o salto entre elas |

O catálogo é [`casos.py`](casos.py) — declarativo. Cada caso traz `nome`, `familia`,
`valores`, `porque` (por que existe), `espera` (`ativa`/`recusa`) e `falha` (a exceção
esperada, quando o caso é de fail-loud).

**`espera` é um pin, não uma descrição.** Todo caso que produz wire declara `ativa` ou
`recusa` — 52 e 17. Só os 3 casos de `falha` ficam em `qualquer`, e ali por construção:
levantam antes de haver rota. Isso importa porque um caso que aceita qualquer rota não
prova nada sobre o FLOOR — vira teste de RT com nome de teste de decisão. Com o pin,
**mudar a decisão do FLOOR quebra o lab**, que é o ponto; quando um ticket mover a
fronteira de propósito (o `T-BN-TIPADO` vai mover 6 destes de `recusa` pra `ativa`),
re-pinar é parte do weld — mesmo regime dos baselines de bytes (ADR-0024).

## Resultado (medido, `report.md`)

- **72 casos, 0 falhas.**
- o bN **ativou em 52**; nos outros o FLOOR escolheu core, denso ou tipado — e **em nenhum**
  o wire ficou maior;
- `encode` determinístico em **100%**;
- **em todos** os casos de rota flat o core sozinho também faz RT.

Casos que valem olhar no [`report.md`](report.md):

- `corpo-rle-vs-bn` — **recusa e recusa certo**: `*100|a`+`*100|b` fecha em 21 B, o bN não
  chega perto. É a prova de que o `min()` está de fato escolhendo;
- `dom-seqrle-colapsa` — o seq-RLE colapsando o **próprio bloco de domínio**, mecanismo
  antigo pegando carona no novo;
- `k-257` — passa do teto (`MAX_W=8`) e o bN se retira, com a **polaridade** ativando no
  lugar (rota `core+pol`);
- `fronteira-n08` — já ativa no menor `n` da largura 8 (17 B contra 29 B).

## Achado colateral: `T-ERRO-SET-ORDEM`

Ao conferir que o lab é reproduzível byte-a-byte, apareceu uma coisa que não é sobre o bN:
`HierarchicalError` interpola um `set` cru na mensagem (`tipos escalares MISTOS {'b', 'n'}`),
e o repr de `set` varia com o `PYTHONHASHSEED`. O wire não muda, o comportamento não muda —
mas a **mensagem** muda de rodada pra rodada, o que quebra diff de evidência.

Registrado como `T-ERRO-SET-ORDEM` no [`STATUS.md`](../../../../STATUS.md); o fix é
`sorted()` na interpolação, em `src/tcf`, que este lab não toca. Enquanto isso o `run.py`
normaliza a mensagem do lado dele (`_normaliza_set`) — remendo declarado, não correção.

Conferido: 4 `PYTHONHASHSEED` diferentes produzem `inputs/`, `outputs/` e `report.md`
byte-idênticos.

## O que este lab NÃO faz

Não mede **ganho em dado real** nem **frequência dos regimes**. As colunas que não ativam
ficam em [`outputs/regimes-que-perdem.md`](outputs/regimes-que-perdem.md), separadas em duas
coisas que são diferentes:

- **§1 — o FLOOR recusou, e recusou certo.** Nada a corrigir; ficam listadas para o estudo
  de volume (*são comuns no dado real?*), que é outro trabalho.
- **§2 — a rota TIPADA nem consulta o bN** (`T-BN-TIPADO`). Essa perda é nossa. A estimativa
  na tabela é o wire bN **construído de verdade** sobre as grafias canônicas que o tipado já
  emite, **com RT conferido**, mais 1 byte pro char de tag. Não é um wire válido hoje — é a
  meta do ticket, ancorada num wire que funciona. Nesta bateria: **3685 B → 469 B em 6
  colunas**. O número que decide o ticket é o de dado real, não este.

## Arquivos

- [`casos.py`](casos.py) — o catálogo declarativo (72 casos, 11 famílias).
- [`run.py`](run.py) — as quatro provas + o relatório. Exit 1 em qualquer falha.
- [`report.md`](report.md) — tabela por família, com rota, bytes, bytes-sem-bN e veredito.
- [`inputs/`](inputs/) — um JSON por caso (amostra + o que se espera).
- [`outputs/`](outputs/) — o `.tcf` e o roundtrip de cada caso, mais
  [`regimes-que-perdem.md`](outputs/regimes-que-perdem.md).

## Origem (dirty → clean)

Labs dirty consolidados aqui:
[polaridade soldada](../../dirty/2026-07/2026-07-27/2026-07-27-1535-polaridade-soldada-single-col-stamp/) ·
[escada de cardinalidade](../../dirty/2026-07/2026-07-27/2026-07-27-1608-escada-bN-cardinalidade-baixa/) ·
[domínio comprimido](../../dirty/2026-07/2026-07-27/2026-07-27-1647-dominio-comprimido-e-alinhamento/) ·
[domínio primeiro (streaming)](../../dirty/2026-07/2026-07-27/2026-07-27-2211-dominio-primeiro-streaming/) ·
[marcador por escape](../../dirty/2026-07/2026-07-27/2026-07-27-2231-marcador-por-escape/) ·
[delimitação espaço completo](../../dirty/2026-07/2026-07-27/2026-07-27-2247-delimitacao-espaco-completo/) ·
[ganho medido na rota tipada](../../dirty/2026-07/2026-07-28/2026-07-28-0829-bn-tipado-ganho-medido/) ·
[canonicidade b64 nas 3 rotas](../../dirty/2026-08/2026-08-06/2026-08-06-2104-b64-canonicidade-3-rotas/) ·
[custo × proteção do b64](../../dirty/2026-08/2026-08-06/2026-08-06-2250-b64-custo-x-protecao/).
Auditoria: [incidente dos 4 bugs](../../dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md).

Decisões: [ADR-0035](../../../../docs/adr/0035-delimitador-de-polaridade-single-col.md)
(polaridade) · [ADR-0036](../../../../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md)
(bN de domínio) ·
[ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md)
(discriminador) ·
[ADR-0037](../../../../docs/adr/0037-denso-b2-ternario-dominio-implicito.md) (denso b2) ·
[ADR-0038](../../../../docs/adr/0038-indice-interno-default-core-tipado-bool.md) (índice
interno) ·
[ADR-0039](../../../../docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md) (lazy bool).

Manual: [`docs/reference/familia-bn-bits.md`](../../../../docs/reference/familia-bn-bits.md).
