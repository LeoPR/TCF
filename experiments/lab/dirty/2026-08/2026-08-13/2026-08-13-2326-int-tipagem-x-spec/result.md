# Resultado — a matriz tipagem × spec para inteiro

14 regimes × 4 células, **0 falhas**. Round-trip verificado com **tipo**
(`type(x) is type(y)`), não só valor — em Python `True == 1` e `1 == 1.0`, e a comparação
ingênua mascararia exatamente o defeito que interessa aqui.

> ### ⚠ Correção de medição (o owner estranhou um wire e tinha razão)
>
> Ao abrir `outputs/gigante-64bit.str-spec.tcf`, o owner: *"parece que quebrou… o número é
> gigante mas o conteúdo não parece fazer sentido. será que o teste de RT deu errado?"*
>
> O RT **não** deu errado — a **medição** é que estava. O wire era:
>
> ```
> #TCF.8 :xioff
> *600+1|\000
> ```
>
> 26 bytes para 600 números de 19 dígitos, porque o `OFFPAD` subtraiu a base e o corpo virou
> `000..599`. **A base de 19 dígitos não está no wire** — ela vivia no objeto do spec que eu
> passava no `decode`. Prova do defeito: o **mesmo wire** devolve `['9223372036854775808']`
> com `base=2**63` e `['0']` com `base=0`, **sem erro nenhum**.
>
> Os números abaixo já estão corrigidos: a coluna `auto-contido` soma o custo do parâmetro
> quando ele **não** é dedutível do corpo.

## A matriz

| regime | str+core | str+spec | *auto-contido* | int+core | int+spec\* | *auto-contido* |
|---|---:|---:|---:|---:|---:|---:|
| `prog-passo1` (1..600) | 36 | **26** | **26** | 37 | **27** | **27** |
| `prog-passo7` | 48 | **27** | **27** | 49 | **28** | **28** |
| `prog-epoch` | 81 | 29 | **40** | 82 | 30 | **41** |
| `prog-base-alta` (1e9+i) | 65 | 26 | **37** | 66 | 27 | **38** |
| `gigante-64bit` (2⁶³+i) | 82 | 26 | **46** | 83 | 27 | **47** |
| `id-aleatorio-6` | 4209 | 3217 | **3217** | 4210 | 3017 | **3017** |
| `id-aleatorio-11` | 7209 | 4730 | **4730** | 7210 | 4217 | **4217** |
| `faixa-0-100` | 1110 | 1110 | 1110 | 1111 | 1044 | **1044** |
| `prog-largura-fixa` | 22 | 22 | 22 | 23 | 30 | 30 → FLOOR recusa |
| `cardinalidade-5` | 333 | 333 | 333 | 334 | 337 | FLOOR recusa |
| `quase-constante` | 25 | 25 | 25 | 26 | 32 | FLOOR recusa |
| `negativos` | 2627 | 2627 | 2627 | 2628 | 2688 | FLOOR recusa |
| `com-nulos` | 240 | 232 | 232 | 241 | 247 | FLOOR recusa |
| `misto-int-float` | 2899 | 2899 | 2899 | 2900 | 3107 | FLOOR recusa |

\* `int+spec` é **simulado** — ver "a célula que não existe", abaixo.

## Achado 0: spec auto-contido × spec parametrizado

A correção acima revelou uma distinção de **design**, não de medição:

| classe | quem | o wire basta? |
|---|---|---|
| **auto-contido** | `PAD` (largura é visível no corpo expandido) · `B94` (`int(b94)` dá o número; zeros à esquerda já são recusados como não-canônicos) | **sim** — o id no header basta |
| **parametrizado** | `OFFPAD` (a base é informação **perdida**, não dedutível de nada) | **não** — o id não basta |

É a mesma linha que separa os specs já soldados: `data-iso`, `cpf`, `cnpj`, `ip` são todos
auto-contidos — o ordinal de data é **absoluto**, não relativo a nada, e por isso
`#TCF.8 :dt\n*600+1|\739617` tem os mesmos 26 bytes **sem nada out-of-band**.

Um spec parametrizado **quebra o self-describing do ADR-0027** (o decode não resolve sozinho
pelo registry). Isso não o inviabiliza, mas muda o que ele é: ou o parâmetro viaja no header
(e aí é extensão de formato), ou o contrato vive nas pontas (e aí é o modo sem-carimbo,
`T-SPEC-SEM-CARIMBO`).

E o preço, agora medido: o OFFPAD continua ganhando, mas menos — **2,03×** no epoch (era
2,79×), **1,78×** no gigante (era 3,15×), **1,76×** na base alta (era 2,50×).

## Achado 1: a tipagem custa 1 byte — e o byte paga a tipagem, não a compressão

**Em todos os 14 regimes, `int+core` custa exatamente +1 byte que `str+core`.** Sempre um,
nunca zero, nunca dois. É o discriminador `n` do header (`#TCF.8n` contra `#TCF.8`).

> **Correção (2026-08-13)**: a primeira versão desta seção dizia que a tipagem *"não entrega
> nada"*. **Errado** — o byte entrega exatamente o que promete. A tag seleciona a **família
> de cast**, e o mesmo corpo devolve coisas diferentes conforme ela:
>
> | wire | volta | tipo |
> |---|---|---|
> | `#TCF.8n\n\1` | `[1]` | `int` |
> | `#TCF.8b\n\1` | `[False]` | `bool` |
> | `#TCF.8s\n\1` / `#TCF.8\n\1` | `['1']` | `str` |
>
> Sem esse byte, `[1,2,3]` voltaria `["1","2","3"]`. Ele **é** o produto.

O enunciado correto é mais estreito: a rota tipada entrega o **cast** e não entrega
**otimização de compressão**. Ela converte para string (via `render`, que para `n` é
literalmente a builtin `str`), entrega ao mesmo núcleo, e usa a tag para converter de volta.
Saber que é inteiro não muda um byte do corpo.

Detalhe que refina isso: dentro da família `n` — que é uma **união** `int|float`, como o
`number` do JSON — o tipo concreto é re-derivado da **grafia**, por elemento. Medido:
`encode([1, 2.0])` volta `[1, 2.0]` com tipos `['int','float']`. Já na família `b` é o
inverso: a grafia é índice de slot congelado (`1`=false, `2`=true) e a **tag é o único
portador do tipo**.

## Achado 2: a célula que não existe

`nature=` **recusa entrada tipada nas três rotas**, com mensagens explícitas:

| rota | recusa |
|---|---|
| single | `kwargs ['nature'] so' valem no flat de STRING` |
| multi | `nature so' aplica a coluna scalar-string (nao objeto/array/inexistente)` |
| `.8H` | `é coluna TIPADA (number/bool), não string — nature aplica só a strings` |

Ou seja: **"entra int, o spec é int, devolve int" não é expressável hoje**. Spec e tipagem
são dois mundos que não se tocam. Por isso a coluna `int+spec` é simulada — transformação
aplicada à mão, custo do corpo + header tipado + tag, round-trip conferido elemento a
elemento com tipo.

E o precedente que o owner citou é preciso: o **bool** já faz o que falta ao int.
`[True, False]` vira `#TCF.8b\n\2\n\1` — `true`→2, `false`→1 pela tabela congelada de
`tipos_internos.py`. Isso *é* um spec semântico embutido na rota tipada. O int não tem o
equivalente.

## Achado 3: os dois eixos são válidos, e dão respostas diferentes

O owner: *"o caso de entrada string e spec int também é válido, mas o lab só tem isso."*
Com a matriz completa dá para ver que os dois eixos não são redundantes:

- **Onde há progressão**, os dois ganham quase igual (o eixo int paga o +1 do `n`).
- **Em ids aleatórios, o eixo int ganha mais**: 3017 contra 3217 (6 dígitos) e 4217 contra
  4730 (11 dígitos). A razão é que, partindo de `int`, a transformação não precisa preservar
  grafia de origem — não há `"007"` para distinguir de `7`.
- **Em `faixa-0-100` só o eixo int ganha** (1044 contra 1110): com fonte string o spec não
  vence o FLOOR, com fonte int vence.

Isso responde a pergunta de fundo: um spec de int para fonte **string** e um para fonte
**int** não são o mesmo objeto com um cast na frente. O contrato de round-trip é diferente —
um devolve grafia, o outro devolve valor — e isso muda o que ele pode fazer.

## Achado 4: o FLOOR recusaria 6 dos 14

`prog-largura-fixa`, `cardinalidade-5`, `quase-constante`, `negativos`, `com-nulos`,
`misto-int-float`. Todos são regimes em que o núcleo já resolve — e a recusa é o
comportamento certo. A simulação reporta o custo **cru** do spec (por isso aparece pior); o
FLOOR real ficaria com o menor.

Vale registrar `misto-int-float`: um spec de **int** encontra `0.5` no meio e tem de recusar
o valor (vira literal), devolvendo `float`. A simulação restaura `type(origem)` justamente
por isso — e foi um erro meu na primeira execução, que estourou em `int('0.5')`.

## Dois erros meus nesta rodada, corrigidos

1. **Filtrei os `None` da simulação**, o que encolhia o corpo e inflava o ganho:
   `com-nulos` aparecia com 186 B e o valor honesto é 247 B — onde o spec **perde**.
2. **Converti a volta com `int()`**, que quebra em coluna mista. O correto é restaurar o
   tipo de origem.

Ambos estão comentados no `run.py`, no ponto exato.

## O que isso implica

- Um spec de inteiro precisa decidir **em qual eixo vive**, e provavelmente nos dois — com
  contratos de round-trip distintos e explícitos.
- Fazer o eixo `int` exige encaixar spec na **rota tipada**, que hoje não tem essa porta. É
  mudança de arquitetura pequena mas real, e o desenho do bool é o modelo pronto.
- O `+1 byte` da tipagem é o preço de saber o tipo. Hoje é puro custo; com spec ele passaria
  a pagar por si em vários regimes.
