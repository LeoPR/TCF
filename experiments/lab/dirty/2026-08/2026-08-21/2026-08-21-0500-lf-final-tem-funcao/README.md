# 2026-08-21-0500 — o último LF: o que tem função e o que é decoração

> ## ⛔ CONCLUSÃO REVOGADA em [`0700`](../2026-08-21-0700-lf-a-resposta/)
>
> Este lab concluiu que o LF final é **redundante e 100% recuperável (55/55)**.
> **Está errado.** O teste era `drop + readd` — operação que **já sabe** que o LF
> existia, e que portanto mede *recuperabilidade*, não *necessidade*. E o corpus
> omitia o único par em que a diferença aparece: **`[]` contra `['']`**.
>
> Uma coluna **vazia** e uma coluna com **um valor vazio** produzem wires que diferem em
> exatamente um LF — o terminador é o que as separa. Ele carrega 1 bit, só no caso de borda,
> e isso basta: **tem necessidade**.
>
> O que continua valendo deste lab: o `.8H` conta o LF dentro do `size`; o custo é de
> 4–6% em payload minúsculo; e a nota sobre `file`/mimetype.

> *"reavalie a necessidade técnica do último `\n` que não tem função e o que tem função. creio
> que não precisamos de caracteres decorativos. até então achei que o último linefeed tinha
> função prática para programas como mimetype e programa `file` para identificar precisavam do
> linefeed final."*

## Primeiro: a minha resposta anterior estava imprecisa

No lab [`0400`](../2026-08-21-0400-lf-final-do-wire/) eu disse que o LF final é **load-bearing**
e que tratá-lo como opcional seria *"indecidível"*. **O owner apontou o buraco**: aquilo só vale
se o LF for **opcional**. Sendo **obrigatório**, ele é **previsível** — e pelo critério do
próprio projeto (dedutível do contexto = redundância de 100%), previsível não deveria viajar.

**Medido: ele É recuperável.** 55 wires, drop do último byte + recolocação na recepção,
**55/55** devolvem o objeto original — incluindo valor vazio no fim, RLE e hierárquico.

Então a pergunta não é "ele carrega informação?" (não carrega). É **"o receptor sabe
recolocá-lo?"**.

## Não é uma coisa só — são três situações

| situação | tem função? |
|---|---|
| **`.8H`** — o LF está **dentro do `size`** declarado do bloco | **SIM.** Não é trailing decorativo: é o último byte de um bloco de comprimento contado. Removê-lo dá `HierarchicalError: size 6 excede o corpo` |
| **single-col e tipado** — terminador do último valor | **Não informacional** — 100% previsível. Mas ver abaixo |
| **multi-col e denso bN** — já **não emitem** | nada a dropar |

## Por que o drop não é seguro hoje (e não é culpa do LF)

**O magic não determina a convenção.** Fuzz sobre as rotas:

| magic | emite LF final? |
|---|---|
| `#TCF.8\n`, `#TCF.8!`, `#TCF.8n` | sempre |
| **`#TCF.8M`** | **às vezes** — `{'a': ['0']}` não; `{'a': ['0'..'4']}` sim |
| **`#TCF.8b`** | **às vezes** — `[False]` sim; `[False,True,True]` não |

Dois magics **ambíguos**. Um receptor que lê o prefixo **não sabe** se deve recolocar.

**E dropar sem recolocar perde dado, em silêncio:**

```
['a', '']  ->  '#TCF.8\na\n\n'
sem o LF   ->  '#TCF.8\na\n'  ->  decode = ['a']     ← o valor vazio sumiu
```

Sem erro e sem warning de diferença. É a classe silenciosa.

**Conclusão precisa**: o LF final **é redundante dentro de cada rota que o emite**, mas dropá-lo
com segurança exige uma **regra global uniforme** que hoje não existe. O obstáculo não é o LF —
é a **assimetria entre rotas**, que já foi medida e precificada como não-vale-consertar
([ADR-0045 §3](../../../../../../docs/adr/0045-bordas-em-valor-de-spec.md): uniformizar quebra o
gate D17a e faz o decoder rejeitar em 2 rotas).

## O que se perde junto, e que não é byte

Hoje o decode do single-col **avisa** quando o LF terminador falta:

> *"corpo single-col sem o LF terminador canônico — decodificando tolerantemente (grafia
> não-canônica; wire possivelmente **truncado** ou editado)"*

Esse warning é um **detector de truncamento**. Dropar sistematicamente o transformaria em ruído:
truncamento real deixaria de se distinguir do normal. **O byte economizado custaria a
capacidade de perceber perda** — e num formato cujo compromisso é roundtrip byte a byte, isso
é caro.

## Quanto vale

| caso | com LF | sem | ganho |
|---|---:|---:|---:|
| 1 CPF | 24 B | 23 B | **4,17%** |
| 3 valores curtos | 16 B | 15 B | **6,25%** |
| 10 valores | 17 B | 16 B | 5,88% |
| 100 valores | 36 B | 35 B | 2,78% |

Não é desprezível: em payload minúsculo — o alvo declarado do `.8` (`O-FMT-15/16`) — são 4–6%.

## Sobre `file` / mimetype

**A crença não procede para identificação.** `file`/libmagic identifica por *sniffing de
conteúdo* (bytes iniciais), não por terminador — e o TCF já tem magic próprio e forte
(`#TCF.8…`), que é exatamente o que essas ferramentas usam.

O que **depende** do LF final é a definição POSIX de *linha* (uma linha termina em newline).
Isso afeta ferramentas orientadas a linha — `wc -l` subconta a última, `read` de shell perde
a última, alguns diffs marcam "\\ No newline at end of file". **Não afeta detecção de tipo.**

Ou seja: sua intuição estava certa sobre *existir* uma razão POSIX, mas ela é sobre
**contagem de linhas**, não sobre **identificação**.

## Recomendação

**Não dropar agora** — mas não pela razão que dei antes. A razão é que o drop exige uniformidade
entre rotas, e a uniformização já foi precificada e recusada. Se um dia o `.8` ganhar um modo de
transporte próprio (a direção *"contrato externalizado + aceleradores"*), o LF final é candidato
legítimo: é redundância de 100%, vale 4–6% em payload pequeno, e o único requisito é que as duas
pontas concordem numa regra por rota.

**O que eu registraria como aprendizado**: "obrigatório" e "informativo" não são a mesma coisa, e
eu tratei como se fossem. Um caractere sempre presente é, por definição, o que a redundância de
100% descreve.

## Não medido (declarado)

- O `.8H` foi verificado só na forma "o size inclui o LF"; não medi se `size` **poderia** ser
  computado sem ele (seria mudança de formato).
- Não medi o custo do LF em corpus real grande — os wires aqui são minúsculos de propósito.
- Não explorei um cabeçalho que **declare** a convenção (custaria ≥1 bit para ganhar 1 byte).

## Evidência

[`run.py`](run.py) com T1–T5 e asserts (T1 exige 55/55 no drop+readd; T2 exige que o magic
**seja** ambíguo, senão a conclusão muda; T3 exige que o drop sem readd perca dado).
7 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/), incluindo o wire que decodifica
errado sem o LF. [`resultado.json`](resultado.json).

## Conexões

- Corrige a leitura de [`0400`](../2026-08-21-0400-lf-final-do-wire/) (o LF é redundante, não
  load-bearing — o que trava o drop é a assimetria)
- [ADR-0045 §3](../../../../../../docs/adr/0045-bordas-em-valor-de-spec.md) — a assimetria
  precificada (H-15-08)
- Direção *"contrato externalizado + aceleradores"* — onde um modo de transporte caberia
