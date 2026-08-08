# Data — consolidado do que sabemos, e o caminho simples

**2026-08-08 · fecha a rodada de data. Nenhum código em `src/tcf`.**

Owner: *"registre as descobertas de data até esgotar as ideias e começar no simples"*.

Cinco labs, um levantamento externo de 21 itens, e um guia. Isto aqui é o que sobra depois
de tirar a teoria — as perguntas em aberto, respondidas, e o que fazer com o resto.

---

## 1. Quanto o OBAT+HCC já faz **sem spec nenhum**

O owner: *"se pensar no básico com o obat+hcc já está legal mesmo vendo data como string
comum (…) se ele for muito string-like ainda assim se beneficia por causa de referências"*.

Está certo — e o número diz **onde** está certo:

| caso | cru | TCF como string | **OBAT sozinho** | melhor spec | **o spec adiciona** |
|---|---:|---:|---:|---:|---:|
| `agrupado` | 6600 | 64 | **99,0%** | 143 | **−123,4%** ⚠️ |
| `diario` | 6600 | 414 | **93,7%** | 22 | +94,7% |
| `k12` | 6600 | 529 | **92,0%** | 237 | +55,2% |
| `espalhado` | 6600 | 5485 | 16,9% | 3132 | +42,9% |
| `mensal` | 6600 | 6338 | **4,0%** | 23 | **+99,6%** |

**A conclusão que isto força:**

> O spec vale muito exatamente onde o OBAT é fraco (`mensal`: 4%), e **é prejudicial onde o
> OBAT é forte** (`agrupado`: o spec piora 123%, porque destrói o RLE que o OBAT explorava).

Isso resolve a dúvida *"o quanto realmente precisa padronizar"*: **não é uniforme**. Uma
coluna de datas agrupadas já está a 99% do teto sem nada. Uma coluna de passo mensal está a
4% e precisa de tudo.

E é o argumento definitivo para o spec ser **candidato do `min()`**, nunca default: sem isso,
o `agrupado` regride.

## 2. Detectar é barato — mas só pelo caminho certo

O owner: *"fazemos ele fazer o rápido e fácil com o mais comum ou mais rápido do Python"*.

Medido, ns por valor (n=20 000, mediana de 7):

| como detectar | ns/valor | contra o mais rápido |
|---|---:|---:|
| `len(v)==10 and v[4]=='-' and v[7]=='-'` | 310 | 1,0× |
| **`date.fromisoformat(v)`** (implementado em C) | **299** | **1,0×** |
| regex compilada | 650 | 2,2× |
| `datetime.strptime(v, "%Y-%m-%d")` | **13 139** | **44×** |

**`fromisoformat` custa o mesmo que olhar 3 caracteres.** Para uma coluna de 1000 datas: 287 µs
contra 13 008 µs do `strptime`.

> **Isto corrige o protótipo.** O `spec_data.py` dos labs usa `strptime` — 44× mais caro pelo
> mesmo resultado. Para ISO, o caminho é `fromisoformat`.

**A ressalva:** desde a 3.11 o `fromisoformat` aceita mais do que emite (`20191204`,
`2021-W01-1`) — então ele precisa do guard de re-emissão (`d.isoformat() != v` → literal).
O guard é uma comparação de string; não muda a ordem de grandeza.

E isso encaixa com o levantamento: `YYYY-MM-DD` é o que a indústria já emite por default, e
é justamente o que o Python detecta mais rápido. **O formato mais comum é o mais barato de
reconhecer** — não é coincidência, é a mesma escolha feita duas vezes.

## 3. As APIs padronizam? Sim — mas em **timestamp**

- **AWS/Smithy**: `@timestampFormat("date-time")`, ISO 8601 com fração de segundo em
  microssegundos ([Smithy 2.0 simple-types](https://smithy.io/2.0/spec/simple-types.html)).
  Há também `ISO_8601_CONDENSED` (`20220425T164413Z`).
- **AWS Systems Manager**: exige ISO 8601, exemplo `2024-05-08T15:16:43Z`
  ([doc](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-datetime-strings.html)).

**Mas repare no que isso confirma**: as APIs padronizam **instante**, não **data**. O
date-only é o caso menos servido pelas convenções — e é exatamente o que estamos tratando.
Quando um pipeline REST entrega "data", ela costuma vir como `…T00:00:00Z`: **24 caracteres
onde 10 bastam**.

---

## 4. As perguntas do owner, respondidas

| pergunta | resposta |
|---|---|
| **forma de padronizar a entrada** | feita: [`docs/how-to/normalizar-data-antes-do-tcf.md`](../../../../docs/how-to/normalizar-data-antes-do-tcf.md) — `YYYY-MM-DD`, RFC 3339 `full-date`, regra em caracteres |
| **quanto realmente precisa padronizar** | **não é uniforme** (§1): de 4% a 99% do trabalho já feito pelo OBAT, dependendo do regime |
| **o TCF detecta fácil os formatos comuns?** | **sim, e de graça** (§2): 299 ns/valor pelo `fromisoformat`, o mesmo que olhar 3 chars |
| **algum modo garante entrada = saída?** | **sim, e é o modo de hoje**: string entra, string volta byte-exata. O spec lazy preserva isso — medido 19/19 |
| **flag para saída semântica (estilo `true`/`false`)?** | ver §5 — a indecisão que sobra |

## 5. A única indecisão que sobra: RT textual × RT semântico

O owner: *"gosto da ideia dele sair como data sem compromisso com a similaridade byte-a-byte,
no estilo do true/false, mas ao mesmo tempo acho que isso poderia ser um tipo de flag. Estou
bem indeciso."*

O que já está estabelecido e **não** precisa de flag:

| entrada | contrato | por quê |
|---|---|---|
| `str` | **RT textual** (byte-exato) | é o contrato de string, e o TCF não pode mudar o que o usuário escreveu |
| `date` nativo | **RT semântico** (volta `date`) | é o contrato do bool, já soldado: `[True]` vira bits e volta `bool` |

**O tipo de entrada já decide.** Uma flag só seria necessária para o caso híbrido — *"entrei
com string, quero receber `date`"* — que é **conversão de tipo**, não compressão, e não é
trabalho do TCF.

> **Recomendação**: não criar a flag. Se o consumidor quer `date`, ele entrega `date`. Se
> entregou string, recebe string. É o desenho do bool, e ele não precisou de flag.

Se algum dia o caso híbrido aparecer com uso real, a flag é aditiva e pode nascer então.

## 6. Hard × lazy — fechado

O owner: *"o TCF não precisa confiar cegamente, apenas vê o spec e tenta; se der errado, faz
fallback string"*. É exatamente o molde do CPF, e está medido:

- **RT: 19/19**, inclusive com o spec errando 100% dos valores;
- **teto do prejuízo: +4,9%** (o marcador de 1 byte por valor);
- **a válvula não mata o ganho**: com 50% da coluna sendo lixo, o lazy ainda ganha 3,1%;
- **ambiguidade custa 0% com FLOOR** — nunca pior que hoje, e em 2 de 4 casos o palpite
  errado ainda ganha.

E o insight do owner sobre **quando** o fallback importa está confirmado em §1: o fallback
para string não é perda, porque a string ainda se beneficia das referências do OBAT. O spec
só precisa ganhar onde o OBAT não alcança.

---

## 7. O caminho simples — o que fazer, em ordem

| # | passo | esforço | mexe em `src/tcf`? |
|---|---|---|---|
| 1 | ~~guia de normalização~~ | — | **feito** |
| 2 | **`SPEC_DATA_ISO` no registry**, detectando por `fromisoformat` + guard de re-emissão | baixo | sim, aditivo |
| 3 | entrar como **candidato do `min()`** — não como default | (é parte do 2) | sim |
| 4 | tipo `date` nativo (contrato do bool) | médio | sim |

O passo 2+3 é o mínimo que colhe o que foi medido, e é pequeno:

```
classify_value  →  fromisoformat + (d.isoformat() != v → literal)
encode_value    →  str(ordinal)  ou  MARCADOR + v
decode_value    →  fromordinal(int).isoformat()  ou  v[1:]
```

Nada de adivinhador no cabeçalho — o owner foi explícito, e §2 mostra que não precisa: o
formato mais comum é o mais barato de reconhecer, e reconhecer não é adivinhar.

## 8. O que fica registrado como NÃO fazer

- **Não** criar detector multi-formato genérico. §1 mostra que o retorno é irregular e §2
  mostra que só o ISO é barato de detectar. Os outros formatos, se vierem, que venham como
  specs nomeados — um por grafia, precedente CPF/CNPJ.
- **Não** usar `strptime` no caminho quente (44× mais caro).
- **Não** usar epoch em segundos como alvo (medido: nunca vence, ×86400 são 5 dígitos sem
  informação).
- **Não** usar base64 como alvo (base-64 contra o base-80 que já temos).
- **Não** criar flag de RT semântico agora (§5).
- **Não** aplicar spec como default (§1: o `agrupado` regride 123%).

---

## Onde estão as evidências

| lab | o que estabeleceu |
|---|---|
| [`2026-08-07-2311`](../../2026-08/2026-08-07/2026-08-07-2311-datas-exploracao/) | o `*N+M\|` já esmaga data; a grafia ISO não alcança; 4 eixos, 90 medições |
| [`2026-08-08-0016`](../../2026-08/2026-08-08/2026-08-08-0016-data-lazy-iso/) | o lazy funciona: RT 19/19, teto +4,9%, a válvula não mata o ganho |
| [`2026-08-08-0235`](../../2026-08/2026-08-08/2026-08-08-0235-data-alvos-e-declaracao/) | 7 alvos; 2 morreram; a declaração inverte metade do quadro |
| [`2026-08-08-1854`](../../2026-08/2026-08-08/2026-08-08-1854-custo-da-ambiguidade/) | ambiguidade custa compressão e não integridade; com FLOOR custa zero |
| [guia](../../../../docs/how-to/normalizar-data-antes-do-tcf.md) | RFC 3339 `full-date`; as exceções nominais (Oracle, .NET, JSON) |
| esta nota | a decomposição OBAT × spec, e o custo de detectar |
