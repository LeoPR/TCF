# Origem HARD × SOFT — o modelo conferido contra o que está implementado

**2026-08-08 · revisão pedida pelo owner: "veja se faz sentido ou se algo foge do que está
implementado, para que a gente melhore"**

---

## O modelo, como foi formulado

| | |
|---|---|
| **origem hard** | o dataset já validou. Se ele aceitou, está certo. O TCF **não revalida** |
| **origem soft** | string com um tipo **declarado**. O TCF tenta aproveitar; se não casar, é *alienígena* |
| **simetria** | se entrou string, volta string |
| **analogia** | CSV: a rigor é tudo string; o tipo se aplica **depois** de ler |
| **telemetria** | o TCF só pode **avisar** que está subutilizado. Corrigir não é dele |
| **profiler** | auxiliar, **sem relação ativa** com o TCF; existe pra o dev entregar o dado bem modelado |

Conferi as afirmações uma a uma contra o código. **Duas se confirmam; uma precisa de
correção; e falta uma categoria inteira no modelo.**

---

## ✅ Confirma: a simetria de origem é exata

```
str      ['str','str']        →  ['str','str']        igual
int      ['int','int']        →  ['int','int']        igual
float    ['float','float']    →  ['float','float']    igual
bool     ['bool','bool']      →  ['bool','bool']      igual
str+null ['str','NoneType']   →  ['str','NoneType']   igual
int+null ['int','NoneType']   →  ['int','NoneType']   igual
```

*"Se entrou string, volta string"* é verdade, e vale também pro contrário: entrou `int`,
volta `int`. O tipo é preservado pela tag no índice 6 (`#TCF.8n`, `#TCF.8b`) e pela grafia.

## ✅ Confirma: o profiler não tem laço ativo

Bate com o ticket `T-FLOW-ENCODE-STRATEGIES-TELEMETRY` (S3): *"gadget paralelo; NÃO altera
`src/tcf` no hot-path"*.

Uma precisão só: **o combustível dele vem de dentro**. O `SideOutputs` é produzido pelo
encode (opt-in, `side_outputs=`), e é isso que torna o profiler de custo zero — o core já
calcula, o profiler só lê. A fronteira não é "o profiler não toca o TCF"; é **"o profiler
não decide nada; ele lê o que o encode já deixou"**.

---

## ⚠️ Precisa corrigir: a regra não é "o que o dataset aceita" — é **o que o JSON aceita**

O modelo diz *"quem avalia o dado no formato primitivo é o dataset; se ele aceita, está
certo"*. Medido, o TCF aceita como origem hard **exatamente o conjunto de escalares do
JSON**, e recusa o resto:

| aceita | recusa (fail-loud) |
|---|---|
| `bool` · `int` · `float` finito · `str` · `None` | `date` · `datetime` · `time` · `timedelta` · `Decimal` · `UUID` · `bytes` · `complex` · **`NaN`** · **`±Inf`** |

Duas consequências:

**1. `NaN` é a exceção ao "o TCF não revalida".** `float('nan')` é um float Python
perfeitamente válido — o dataset aceitou — e o TCF **recusa**, citando a RFC 8259. Ou seja: o
TCF *julga* um valor de origem hard. É justificado e está registrado, mas contradiz a regra
como enunciada. A regra real é: **quem decide não é o dataset, é o JSON.**

**2. `Decimal` está recusado junto com `date`.** Os dois tipos mais comuns num dataset real
depois dos escalares JSON — dinheiro e data — não entram. Isso importa porque `Decimal` é
precisamente o tipo que existe *para não virar float*, e mandá-lo como string é jogar fora a
informação de que era decimal.

---

## ❌ Falta no modelo: existe uma **terceira** categoria

O modelo tem duas caixas (hard e soft). A implementação tem três:

| categoria | exemplo | o que acontece hoje |
|---|---|---|
| **hard aceito** | `bool` `int` `float` `str` `None` | aceita, preserva tipo, comprime |
| **hard RECUSADO** | `date` `Decimal` `UUID` `NaN` | **fail-loud** — nem string vira |
| **soft** | string + `nature=SPEC_CPF` | tenta, e o que não casar vira literal |

A caixa do meio é a que não está no modelo, e é onde mora quase todo o trabalho futuro de
tipos. Ela **não é** "alienígena" no sentido do soft — alienígena no soft é um valor que
*não casa com o spec* e cai no literal, sem drama. Aqui é o oposto: o dado é legítimo, o
dataset o aceitou, e o TCF **se recusa a receber**.

Vale nomear a diferença porque as duas coisas soam parecidas e têm remédios opostos:

- **alienígena no soft** → escape de 1 byte, segue a vida (medido: pior caso +4,9%);
- **recusado no hard** → o chamador tem de converter pra string ANTES, e ao fazer isso
  **perde o tipo** — que é exatamente o que o modelo quer evitar.

---

## A analogia do CSV: meio certa, e o "meio" é o que interessa

*"A rigor o CSV é sempre string; o tipo se aplica depois."*

Verdade pro CSV, e verdade pra **metade** do TCF. A outra metade já é tipada: `#TCF.8n`,
`#TCF.8b`, o denso `b1`/`b2`, o lazy `bB`, e agora o `nB`. O TCF **já não é CSV** — ele tem
caminho hard, só que incompleto.

Isso é bom, e reenquadra o trabalho de data: **não é criar um caminho novo, é completar um
que já existe.** O `int` fez o percurso inteiro (nativo → tag → denso). O `date` não fez
nenhum passo.

---

## A camada soft já tem um embrião de schema

`encode(..., nature_per_col={"col": SPEC})` — `src/tcf/encoder.py:231`. Isso **é** um schema
por coluna, em embrião: um dicionário de coluna → tipo declarado.

Specs existentes: `SPEC_CPF`, `SPEC_CNPJ` (templated+checked) e `SPEC_IP` (templated+padded),
com `SPEC_REGISTRY` pra resolução self-describing pelo header.

Então *"declarar como tipo data no schema passado na lib encode"* não precisa de mecanismo
novo — precisa de **um `SPEC_DATA` no registry**. É o mesmo lugar, a mesma API, o mesmo
header self-describing.

---

## O que eu proporia melhorar (não são tickets prontos)

1. **Fixar o vocabulário das três caixas** — hard-aceito / hard-recusado / soft. Sem isso,
   "alienígena" quer dizer duas coisas com remédios opostos.
2. **Trocar "o dataset decide" por "o JSON decide"** na formulação. É o que está
   implementado, é defensável (JSON é o alvo prático registrado), e explica sem exceções por
   que `date` e `Decimal` caem.
3. **`SPEC_DATA` no registry** — o caminho mais curto pro que já foi medido. Nada de mecanismo
   novo: um spec a mais, do lado soft, herdando o `nature_apply` de telemetria.
4. **Registrar `Decimal` junto com `date`** como hard-recusado. Não pra fazer agora — pra não
   descobrir depois que a decisão de data fechou de um jeito que não serve pra dinheiro.

Nenhum código mexido nesta nota.
