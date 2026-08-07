# Família bN — bits densos de domínio (`#TCF.8B` / `#TCF.8C`)

> **Estado: preliminar.** Descreve o comportamento **soldado e medido** hoje (`#TCF.8`).
> É referência de comportamento, ainda não o manual final — a redação será revista quando
> a família fechar (ver [O que ainda não está aqui](#o-que-ainda-não-está-aqui)).
>
> Decisões: [ADR-0036](../adr/0036-bn-de-dominio-cardinalidade-baixa.md) (bN de domínio) ·
> [ADR-0035](../adr/0035-delimitador-de-polaridade-single-col.md) (polaridade) ·
> [ADR-0029](../adr/0029-version-format-identification-semi-implicit.md) (discriminador).
> Contraprova: [EXP-016](../../experiments/lab/clean/EXP-016-bn-familia-bits/) — 72 casos,
> 11 famílias, 0 falhas.

## O que é

Quando uma coluna tem **poucos valores distintos**, guardar cada célula por extenso é caro:
o que varia de linha para linha não é o valor, é **qual dos poucos valores** é. O bN grava o
conjunto de valores **uma vez** (o *domínio*) e o resto vira **índices em bits**, empacotados
em base64.

```
['a','b'] * 50            →  #TCF.8B164↵a↵b↵=VVVVVVVVVVVVVVVVUA          34 B
```

Cada célula custa **1 bit**. As mesmas 100 células por extenso custariam 200 B de corpo.

O bN é **opção de tamanho, nunca de correção**: o core sozinho codifica e decodifica todas
essas colunas. Ele entra como **candidato** num `min()` — se não for menor, não é escolhido.
Essa invariante é testada caso a caso no EXP-016 (prova *nunca-pior* e prova *correção ≠ bN*).

## O wire

```
#TCF.8 B  w  n ↵  <domínio, uma linha por valor> ↵ = <base64 dos índices>
       │  │  │
       │  │  └─ n = número de células, em hex minúsculo, sem zero à esquerda
       │  └──── w = bits por índice = ceil(log2(k)), 1..8
       └─────── discriminador: B = domínio primeiro · C = domínio por último
```

O discriminador mora no **índice 6** da linha 1 — o slot de tag de tipo do `#TCF.8`
(ADR-0029). Nada é declarado além disso: `k` (tamanho do domínio) se deduz contando as
linhas, e `w` já está no header.

### Os dois modos

| modo | forma | quando |
|---|---|---|
| **`B`** — domínio primeiro | `#TCF.8B<w><n>↵<domínio>↵=<b64>` | **default.** O leitor já tem a tabela de tradução quando os bits começam a chegar — serve streaming |
| **`C`** — domínio por último | `#TCF.8C<w><n>↵<b64>↵<domínio>` | lote. Decodável, não emitido pelo encoder de hoje |

`C` é *decodável-não-emitido*: o decoder aceita, o encoder não produz. É o mesmo precedente
dos nomes `true`/`false` no bool tipado — a forma existe no wire para quem a escrever, sem
custar uma decisão no encode.

### O marcador `=`

O `=` separa o domínio dos bits. Ele não é adorno: no modo `B` o bloco de domínio tem
tamanho variável e é o `=` que diz onde ele acaba, **sem contador**. Escolhido porque é o
char de padding do base64 — já pertence ao vocabulário do payload.

Se um valor do domínio começar com `=`, ele leva um escape:

```
['=a','b'] * 30           →  #TCF.8B13c↵\=a↵b↵=VVVVVVVVVVA               29 B
```

Só a **primeira** posição da linha importa — `a=b` não é ambíguo e não paga nada.

## Domínio: como os valores são gravados

O bloco de domínio é **um corpo TCF comum**, produzido pelo mesmo compressor de coluna do
core. Isso significa duas coisas:

1. **os mecanismos do core valem lá dentro** — um domínio com repetição adjacente colapsa em
   seq-RLE, sem nenhum código novo;
2. **o escape do core vale lá dentro** — `\` vira `\\`, e o primeiro dígito de cada corrida de
   dígitos vira `\<dígito>`. Nada disso é regra da família bN; é a gramática de sempre.

Nos exemplos abaixo, à esquerda está o valor **real** (uma contrabarra é uma contrabarra) e à
direita o wire literal:

```
valor = contrabarra + "x"   →  #TCF.8B13c↵\\\\x↵b↵=VVVVVVVVVVA          31 B
valores "0" e "1"           →  #TCF.8B13c↵\\\0↵\1↵=VVVVVVVVVVA          31 B
valores "" e "a"            →  #TCF.8B13c↵↵a↵=VVVVVVVVVVA               26 B
```

O caso `['0','1']` é o mais caro dos três e mostra por quê: `0` é gravado como `\0` (a grafia
que distingue o valor `"0"` do slot nulo), e aí o core escapa o `\` **e** o dígito.

### O slot nulo

`None` ocupa o **slot 0**, pré-alocado. Ele não define o tipo da coluna e convive com
qualquer domínio:

```
['s','n',None] * 20       →  #TCF.8B23c↵\0↵s↵n↵=YYY…                    39 B
```

A grafia é **injetiva por construção**: `None` → `0`; qualquer valor que *seria* grafado `0`
ou que já comece com `\` recebe um `\` na frente. Sem isso, `"0"` e `None` colidiriam — e
colidiam, silenciosamente, até a auditoria de 2026-07-28
([incidente](../../experiments/lab/dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md)).

## Quando o bN ativa

`k` = número de valores distintos (incluindo o slot nulo, se houver).

A largura é `w = ceil(log2(k))` — **não** arredondada pra potência de 2. Um domínio de 5
valores usa 3 bits, não 4; um de 100 usa 7, não 8. É o `_largura` em
`composicional/dominio_bn.py`.

> Esta tabela estava errada aqui (dizia `w ∈ {1,2,4,8}`) até 2026-08-07. Agora ela é
> **gerada do código** em
> [`EXP-016/outputs/tabela-larguras.md`](../../experiments/lab/clean/EXP-016-bn-familia-bits/outputs/tabela-larguras.md),
> e o lab falha se as faixas deixarem de ser contíguas — a cópia abaixo é conferida, não
> digitada.

| `k` | `w` | o que acontece |
|---:|---:|---|
| 1 | 0 | **não ativa** — o core resolve com RLE (`*100\|a`, 14 B) |
| 2 | 1 | ativa |
| 3–4 | 2 | ativa |
| 5–8 | 3 | ativa |
| 9–16 | 4 | ativa |
| 17–32 | 5 | ativa |
| 33–64 | 6 | ativa |
| 65–128 | 7 | ativa |
| 129–256 | 8 | ativa |
| ≥257 | 9 | **não ativa** — passa do teto `MAX_W=8` |

Isso importa pro `T-BN-LARGURA-VARIAVEL`: o desperdício não é o arredondamento pra potência
de 2 (não existe), é o arredondamento pro **inteiro** — `k=5` gasta 3 bits onde a entropia
pede 2,32.

Ativar não é automático: mesmo dentro da faixa, o `min()` pode preferir outro mecanismo. O
caso mais claro é o corpo perfeitamente RLE-ável:

```
['a']*100 + ['b']*100     →  #TCF.8↵*100|a↵*100|b↵                      21 B   (o bN perde)
```

Dois blocos de RLE custam 21 B; nenhum esquema de bits chega perto disso. **É o
comportamento certo** — o FLOOR está fazendo o trabalho dele.

## Integridade do payload base64

Toda leitura de bN valida o payload com **três checagens**, e nenhuma subsome as outras:

| checagem | pega o quê |
|---|---|
| `b64decode(validate=True)` | char fora do alfabeto base64 |
| re-codifica e compara | **os valores** — bits mortos no último byte que decodificam igual mas foram adulterados |
| tamanho exato esperado | payload truncado ou estendido |

As duas primeiras são praticamente de graça; a segunda é a única que protege **valor**, não
só forma. O custo medido das três somadas é **0,17–0,58% do decode**
([lab 2026-08-06-2250](../../experiments/lab/dirty/2026-08/2026-08-06/2026-08-06-2250-b64-custo-x-protecao/))
— por isso ficam **sempre ligadas**, em vez de virarem knob.

Wire não-canônico **falha alto**. A exceção é a classe de tolerância já ratificada: tolerar
só quando o valor recuperado é *provadamente* o mesmo, e ainda assim com warning
([política](../../experiments/lab/dirty/notas/2026-08/2026-08-06-2329-tolerancia-vs-erro-politica-de-wire-nao-canonico.md)).

## Canonicidade — o que o decoder recusa

O encoder emite **uma** forma para cada coluna; o decoder recusa as outras, mesmo quando
seriam legíveis. Isso mantém `encode` determinístico e o wire diffável.

- **header**: zero à esquerda em `n`, hex maiúsculo, `0x`, sinal, `_` do PEP-515, dígito
  Unicode — todos recusados (a checagem é por **re-emissão**: `f"{n:x}" != nhex` → erro);
- **conteúdo depois do bloco de bits** — recusado;
- **slot de domínio não referenciado** — recusado. Todo slot `0..k-1` aparece nos índices,
  porque o domínio é construído *pela primeira aparição*. Um domínio com slot sobrando não
  foi produzido por este encoder.

## Interação com a camada de borda (polaridade)

A polaridade (ADR-0035) é uma camada **de borda**: o encode polariza **depois** do corpo
canônico, o decode despolariza **antes** de qualquer despacho. O bN nunca vê corpo
polarizado, e o seq-RLE nunca vê corpo polarizado. As duas camadas se compõem sem se
conhecer — no EXP-016 elas aparecem juntas na rota `core+pol`.

O sufixo de polaridade é 1–2 chars **iguais** de pontuação no fim da linha 1. A separação é
inequívoca porque a faixa do delimitador exclui dígito e letra, e nenhum discriminador é
pontuação.

## O que ainda não está aqui

Comportamento **conhecido e medido**, mas ainda não soldado — cada um é ticket aberto no
[`STATUS.md`](../../STATUS.md):

| ticket | o que falta |
|---|---|
| `T-BN-TIPADO` | a rota tipada (`#TCF.8n`/`#TCF.8b`) **não consulta** o candidato bN. É a maior lacuna medida — ver [§2 de `regimes-que-perdem.md`](../../experiments/lab/clean/EXP-016-bn-familia-bits/outputs/regimes-que-perdem.md) |
| `T-BN-LOTE` | o modo `C` é decodável mas nunca emitido |
| `T-BN-LARGURA-VARIAVEL` | `w` é uniforme; larguras mistas não foram exploradas |
| `T-BN-MULTICOL` | o bN só entra na rota single-col |
| `T-BN-GZIP` | como o bN se comporta sob compressor externo |
| `T-DENSO-PADDING` | os bits mortos do último byte |

**Não medido aqui:** frequência dos regimes em dado real. O EXP-016 é sintético por
construção; ele mostra *que* comportamento existe, não *quanto* ele aparece.

## Onde olhar

- contraprova executável: [`EXP-016`](../../experiments/lab/clean/EXP-016-bn-familia-bits/)
  (`python run.py`, exit 0 só se tudo fechar)
- implementação: `src/tcf/composicional/dominio_bn.py` ·
  `src/tcf/composicional/polaridade.py`
- testes: `tests/test_dominio_bn.py` (123) · `tests/test_polaridade.py` (32)
