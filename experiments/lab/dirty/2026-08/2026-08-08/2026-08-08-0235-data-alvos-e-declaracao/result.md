# Resultado — alvos de data × declaração da grafia

**2026-08-08 · dirty · 56 medições, `n=600`, RT em dois níveis, 0 falhas**

---

## 1. Dois alvos morreram, e o motivo é estrutural

| alvo | vence em algum regime? | por quê |
|---|---|---|
| `epoch-seg` | **nunca** | multiplicar por 86400 acrescenta **5 dígitos sem informação nenhuma** |
| `ordinal-b64` | **nunca** | base64 é base-**64**; o denso é base-**80**. Mesma largura de 4 chars, alfabeto menor → empata ou perde |
| `iso` | 1 de 8 | é a linha de base; nunca é ótima |

O `epoch-seg` responde à hipótese *"formato em segundos"*: para **data pura**, é
desperdício puro. Só faria sentido se houvesse hora — e aí não é mais data.

O `ordinal-b64` responde à hipótese *"comprimir no mesmo estilo do base64"*: **já temos algo
melhor**, que é o alfabeto de 80 chars da nature do CPF. O base64 desperdiça 16 símbolos.

## 2. A declaração da grafia **inverte metade do quadro**

Sem contar a declaração, o campeão era o `ordinal-dec` (até **275×** sobre o ISO). Pagando
os **10 B** do header (`#TCF.8 :data-iso`, medido), ele **não vence em regime nenhum**.

| regime | sem declarar | pagando |
|---|---|---|
| `diario` | `ordinal-dec` | **`delta-dias`** ← |
| `semanal` | `ordinal-dec` | **`delta-dias`** ← |
| `mensal` | `ordinal-dec` | **`delta-dias`** ← |
| `agrupado` | `compacto` | **`iso`** ← |
| `repetido-k12` | `delta-dias` | `delta-dias` |
| `espalhado` | `ordinal-denso` | `ordinal-denso` |
| `espalhado-ord` | `delta-dias` | `delta-dias` |
| `decada-espalhada` | `ordinal-denso` | `ordinal-denso` |

**Placar final: `delta-dias` 5 · `ordinal-denso` 2 · `iso` 1.**

E a inversão **não é efeito de escala**: nos regimes regulares os dois alvos colapsam para
tamanho constante em `n` (o RLE come tudo), então 22+10 contra 27 vale para qualquer `n`.

## 3. Por que o `delta-dias` ganha: ele **carrega a própria grafia**

Conferido no wire:

```
delta-dias  →  #TCF.8!!↵2026-01-01↵*599|1        o 1º valor sobrevive VERBATIM
ordinal-dec →  #TCF.8↵*600+1|\739617             a grafia sumiu
ordinal-denso → #TCF.8!!↵&O+S↵&Nyv↵…             opaco
```

O `delta-dias` guarda o primeiro valor por extenso — porque precisa dele como base da
soma. De brinde, **a grafia viaja no wire sem custo adicional**: o decode lê `2026-01-01`,
infere que é ISO, e aplica a mesma grafia na volta.

Isso responde à terceira hipótese do owner — *"o primeiro registro ser formatador"* — com um
achado melhor do que a ideia original: **não é preciso acrescentar um template**; um dos
alvos já paga isso como efeito colateral do que ele faz de qualquer jeito.

## 4. Inferir a grafia do 1º valor: **100% para ISO**

Sobre as 366 datas de um ano, quantas vezes o primeiro valor tem leitura única:

| grafia | taxa | exemplo ambíguo |
|---|---:|---|
| `iso` · `compacto` · `ponto` · `iso-invertido` | **100%** | — |
| `br` · `us` | **60,4%** | `01/01/2026` → `['br','us']` |

Só o par BR/US é ambíguo, e **só entre si**: os 39,6% que falham são as datas de dia ≤ 12.

**Mas a inferência só é utilizável se o alvo preservar o 1º valor.** Hoje isso só vale para
o `delta-dias`. Nos outros, preservar o primeiro valor custaria 11 B (`2026-01-01` + LF) —
**pior que os 10 B do header**.

---

## As três perguntas respondidas

**1. *"`date-iso` seria uma lib que tenta adivinhar o formato?"***
Não, e são coisas separadas. Adivinhar **não substitui declarar**: se o encoder escolhe uma
grafia e não registra qual, o decode não tem como inverter — a grafia se perde na
transformação. O sniff é **front-end** da declaração, não alternativa a ela. E, pelo que já
foi medido, errar o palpite custa bytes e nunca dado, então o sniff pode ser preguiçoso.

**2. *"o decode pode descomprimir e depois aplicar um verificador do tipo e reconverter?"***
A reconversão já é o que a inversa do spec faz. O **verificador** é que não cabe: o decode
não precisa verificar, precisa **inverter**. Verificar na volta seria revalidar o dado — o
oposto de *"o TCF aproveita o tipo, não corrige o tipo"*.

**3. *"o primeiro registro ser formatador"***
Funciona, e mediu 100% para ISO. Melhor ainda: **o `delta-dias` já faz isso de graça.** Não
é preciso inventar um campo de template.

---

## O que isso sugere

1. **Três alvos bastam**: `delta-dias`, `ordinal-denso`, `iso` (identidade). Os outros quatro
   são dominados nas medições.
2. **`delta-dias` é o default natural** — vence 5 de 8 regimes e resolve a declaração sozinho.
3. **O header `:data-*` só é necessário para os alvos que destroem a grafia** — hoje, só o
   `ordinal-denso`, e só nos 2 regimes espalhados.
4. **BR/US é a única ambiguidade real**, e só entre si. Fora desse par, a grafia se lê do
   primeiro valor.

## O que este lab NÃO fez

- Só **data**, sem hora — recorte do owner. `epoch-seg` pode reviver com timestamp.
- `n=600` fixo; a varredura em `n` não foi feita (embora a inversão do §2 não dependa dela
  nos regimes regulares, por serem O(1)).
- Não mede o custo do `min()` entre alvos (materializar 3 candidatos custa CPU — é `.9`).
- Não testa **coluna suja** — este lab é de alvos, não da válvula de escape; a sujeira foi
  medida no lab `2026-08-08-0016`.
- A inferência foi medida sobre um ano de datas; não sobre distribuições reais.
