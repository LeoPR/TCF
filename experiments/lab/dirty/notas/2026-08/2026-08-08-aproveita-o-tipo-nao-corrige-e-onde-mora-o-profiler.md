# "O TCF aproveita o tipo, não corrige o tipo" — e onde mora o profiler

**2026-08-08 · confirmação de modelo + recuperação de decisão já registrada**

---

## O raciocínio, como eu entendi

1. O TCF **se aproveita** do tipo para otimizar. Ele **não corrige** o tipo.
2. Data que entra **tipada** → não há falha possível; o tipo já garante.
3. Data que entra **como texto com intenção declarada** → lazy, e se der problema, escape.
   Só isso.
4. **"Data inválida" não existe à rigor pro TCF.** Existe *dado com problema que não
   aproveita a compressão*.
5. Manter o dado saudável é responsabilidade do arquiteto, não do formato.
6. **Mas não é pra ignorar**: uma coluna que se diz data e está com problema **prejudica o
   algoritmo** — por isso a telemetria importa.
7. Pessimismo do dado não é pra super-dedicar; serve pra **guiar o que prejudica
   performance**.

Entendi assim, e concordo. Abaixo o que isso **decide**, que é onde o modelo passa de
opinião a consequência.

---

## A consequência forte: `status` não é taxonomia de ERRO, é de PERDA

Se "inválido" não existe, então a classificação de um valor não-compressível não é um
diagnóstico de erro — é a **medida de quanto a coluna deixou na mesa**.

Isso decide o **canal**, que era a pergunta em aberto de ontem:

| canal | serve pra | cabe aqui? |
|---|---|---|
| exceção | contrato violado | **não** — não há contrato violado |
| warning no encode | degradação que o chamador precisa ver **agora** | **não** — dispara em operação normal e vira ruído |
| **telemetria** | quanto se perdeu, e por quê | **sim** |

E fecha o círculo do que eu argumentei ontem contra o *"light warning"*: eu tinha o canal
certo pelo motivo errado (achei que era ruído); o motivo real é mais forte — **não é erro,
então não é warning.**

---

## E o canal já existe, já populado

`SideOutputs.nature_apply` (`src/tcf/side_outputs.py:38`) já carrega exatamente isso, por
coluna. Conferido agora, rodando com a nature do CPF sobre uma coluna de placeholders:

```json
{"val": {"spec": "cpf", "total": 50, "compressible": 20, "apply_rate": 0.4,
         "by_status": {"compressible": 20, "length_wrong": 10,
                       "empty_value": 10, "format_mismatch": 10}}}
```

`apply_rate` é literalmente *"quanto desta coluna aproveitou o tipo"*. `by_status` é
*"e o resto, por quê"*.

**Uma nature de data herda isso de graça.** A taxonomia que o protótipo de ontem já produz
(`comprimento`, `nao-parseia`, `grafia-nao-canonica`, `nulo`, `vazio`) é o mesmo formato.
Não há nada a inventar — há um campo a preencher.

O comentário no próprio arquivo diz pra onde isso ia: *"Habilita auto-detect informado no
futuro (Fase 3 schema natures)"*.

---

## O profiler: recuperado, e estava decidido

> *"nem lembro o que a gente ia fazer com ele, se ia deixar como acessório, dentro, etc…"*

Está em [`tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md`](../../../../tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md)
— **status `open`, P2, criado 2026-07-05**. O ticket chama de **S3**, e a nota de contrato
externalizado o chama de *"embrião do profiler"*.

**A decisão de onde mora estava tomada: acessório.**

> *"**É**: análise offline/sampling + sugestão/warning; **NÃO altera `src/tcf` no hot-path;
> é gadget paralelo.**"*

E mais três coisas que estavam decididas:

| decisão | onde |
|---|---|
| **Consome `SideOutputs`** — "só o que já se calcula", custo zero | ticket, §telemetria |
| **Alert-only** — "só detecta, nunca arruma" | ticket, alinhado aos gadgets |
| **Droppable por construção** — classe de aceleração; perder o sidecar não perde dado | `contrato-externalizado`, `H-ACCEL-SIDECAR-01` |

A tese do S3, que é o que dá sentido a tudo: **não pagar a otimização por encode (S2);
pagá-la 1× offline (S3)**, analisando amostras e sugerindo ao produtor emitir já na forma
ótima.

Isso encaixa exatamente no que foi levantado agora — *"o dev dá um volume e formato de dados
e o profiler faria uma avaliação geral"*. É o S3, com outro nome.

Quatro itens de aceite, **nenhum feito**.

### A armadilha de vocabulário: são DOIS warnings

O ticket prevê *"modo ATIVO (warning)"*, e ontem eu argumentei contra warning. Não há
conflito — são coisas diferentes com o mesmo nome:

| | quando dispara | quem lê | veredito |
|---|---|---|---|
| warning do **encode** | toda vez que um valor cai no literal, em produção | ninguém, depois da terceira vez | **não** |
| warning do **profiler** | offline, sob demanda, na ferramenta de dev | o dev, que pediu | **sim** |

O ticket fala do segundo. Vale fixar o vocabulário antes que alguém implemente o primeiro
achando que está seguindo o ticket.

---

## Onde eu refino o raciocínio — um ponto

> *"se o tipo data entrar como data, nunca terá falha e o TCF sempre vai funcionar"*

Verdade **quando existir**. Hoje não existe:

```
encode([datetime.date(2026,1,1)])      →  HierarchicalError: valor escalar de tipo
                                          não suportado: date
encode([datetime.datetime(...)])       →  idem
```

Data nativa **fail-loud** hoje. Então os dois ramos do raciocínio não são duas opções
disponíveis — **o lazy é o único ramo que existe**, e o ramo "entra tipada" é trabalho
futuro (e é o mesmo problema do schema prévio que foi mencionado).

Isso é bom para o recorte: reforça que o lazy é o lugar certo pra começar, e não uma escolha
entre dois caminhos.

E quando o ramo tipado existir, ele terá **uma** decisão que o lazy não tem: **qual grafia
emitir na volta**. Um `date` nativo não traz formato; o TCF vai ter de escolher. Não é
falha — é um default a decidir, e é bom saber que ele existe antes de chegar lá.

---

## O que fica

- O modelo está confirmado e é o que orienta a nature de data.
- O canal da telemetria **já existe e já funciona** — falta a nature de data usá-lo.
- O profiler é **acessório**, `T-FLOW-ENCODE-STRATEGIES-TELEMETRY` (S3), aberto desde
  2026-07-05, alert-only, droppable, consumindo `SideOutputs`. Nada a redecidir.
- **Data tipada nativa não existe** e é `fail-loud` hoje — registrar como trabalho futuro,
  irmão do schema prévio.

Nenhum código mexido nesta nota.
