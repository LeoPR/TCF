# 2026-08-06-2104 — Canonicidade de payload b64 nas TRÊS rotas

Refaz o lab [`2026-08-06-2006-bn-b64-validate`](../2026-08-06-2006-bn-b64-validate/), que
tinha método bom (evidência materializada, matriz, proveniência) mas **três conclusões
frouxas**. O conteúdo científico dele se mantém; o que muda é o que se conclui dele.

## O que o lab anterior estabeleceu, e continua valendo

`decode_bn` decodava sem `validate=True` e vazava `binascii.Error` cru onde o denso responde
com mensagem de nível TCF. **Confirmado.**

## Correção 1 — o lazy `bB` não era padrão-ouro

O lab anterior o classificou junto com o denso: *"FAIL-LOUD TCF em 48/48 — o padrão-ouro
segura a bateria inteira"*. Não segurava:

| rota | payload + `AAAA` (bytes zero, base64 válido) |
|---|---|
| `bn-B` | **SILENCIOSO-IGUAL** |
| `denso-b1` · `denso-b2` | fail-loud |
| **`lazy-bB`** | **SILENCIOSO-IGUAL** |

A sonda anterior não separava os dois porque a extensão que ela usava caía na checagem de
bits-de-padding do `unpack_w`. Estender com bytes que **são** zero atravessa essa checagem.

**Consequência: a correção vai em duas rotas, não em uma.**

## Correção 2 — `tamanho exato` não era variante opcional

O lab anterior a chamou de "recomendação" e ofereceu duas variantes sem convergir. Medindo
qual checagem pega o quê:

| adulteração | `validate` | re-codifica | tamanho |
|---|:-:|:-:|:-:|
| char inválido `!` · espaço | **PEGA** | — | — |
| padding `==` a mais | passa | **PEGA** | passa |
| caixa trocada | passa | **PEGA** | passa |
| extensão zero `+AA` / `+AAAA` | passa | passa | **PEGA** |
| truncado −4 | passa | **PEGA** | **PEGA** |

**Nenhuma subsome a outra.** As três são o mínimo — e são exatamente o que o
`_decode_denso` já fazia.

## Correção 3 — o padding não era decisão nova

O lab anterior deixou como *"decisão do owner: se a canonicidade S1.2 for estendida ao
payload"*. Ela já estava decidida: re-codificar-e-comparar é a **mesma técnica** que o
cabeçalho usa para o hex (`f"{n:x}" != nhex`, ADR-0036). A regra existia; faltava aplicá-la
a outro campo.

## O achado novo: o `s9` separa sintaxe de conteúdo

O lab anterior reportou **0 corrupção**. Havia 3 células — a sonda de caixa trocada não
estava na bateria dele.

```
bn-B, payload …GGGGGE → …GGGGGa
  valores 198 e 199:  ['v0','v1'] → ['v1','v2']    silenciosamente
```

E a diferença entre as células **não é acaso**:

| rota | bytes | último char tem bits mortos? | s9 |
|---|---|:-:|---|
| `bn-B` · `bn-C` · `denso-b1` · `denso-b2` | 25/50 B | **sim** | a re-codificação **pega** |
| `lazy-bB` | 75 B (= 25×3) | não | **nenhuma checagem pega** |

Quando o payload não fecha em grupo de 3 bytes, o último char carrega bits que não
significam nada — trocá-lo produz **grafia não-canônica dos mesmos bytes**, que é sintaxe.
Quando fecha exato, todos os bits significam e a troca é **conteúdo** — fora do alcance de
qualquer validação sintática.

Dos 3, **2 são sintáticos** (fechados) e **1 é de conteúdo** (fora de escopo, seria
checksum).

## A matriz — 9 sondas × 5 rotas

| | fail-loud TCF | binascii cru | silencioso | corrompe |
|---|:-:|:-:|:-:|:-:|
| **hoje** | 31 | **6** | **5** | **3** |
| **proposto** | 44 | 0 | 0 | 1 (conteúdo, fora de escopo) |

45 células, cada uma com wire em `outputs/sondas/<rota>-<sonda>.tcf`, **relido do disco**
antes do decode. Matriz completa em `outputs/matriz-sondas.csv`.

## Byte-neutralidade

Os wires válidos das 5 rotas passam pela proposta, e o roundtrip é byte-idêntico ao
consumido (`cmp` entre `intermediates/*-consumido.json` e `outputs/*-roundtrip.json`). A
mudança só toca caminho de erro.

## Um bug do próprio lab, que o assert pegou

A primeira rodada rejeitou o wire **válido** do `lazy-bB` (*"Leading padding not allowed"*):
meu extrator de payload olhava o **discriminador** (índice 6), e o lazy é `b` ali — caía no
ramo do denso e levava o `=` junto. O lazy usa a **mesma grafia do bN modo B**. Passou a
localizar **pelo marcador**, não pelo discriminador.

Vale registrar porque é a terceira vez que "olhar o índice fixo em vez da estrutura" morde
neste projeto.

## Weld

| onde | mudança |
|---|---|
| `dominio_bn.valida_payload_b64` | **fonte única** das três checagens (nova) |
| `dominio_bn.decode_bn` | passa a chamá-la (não tinha nenhuma) |
| `decoder._decode_lazy_bool` | passa a chamá-la (tinha só o `validate`) |
| `decoder._decode_denso` | **nada** — já era o padrão, e foi o modelo |

Suíte **1105 passed**; `test_dominio_bn.py` 58 → **88**. Gates inalterados.

## Rodar

```
python run.py
```
`proposta.py` tem as três checagens isoladas e o `por_que_cada_uma`, que é o que prova a
independência.
