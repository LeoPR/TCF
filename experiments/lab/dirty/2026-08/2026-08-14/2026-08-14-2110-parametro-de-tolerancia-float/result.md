# Resultado — o parâmetro de tolerância funciona, e a verificação é quem manda

12 pedidos × 3 colunas (1 sintética + 2 reais), **0 falhas**. Orienta, não fecha.

## A forma que sobreviveu

```python
Tolerancia(quantum=0.01, mode="half-even")   # grade de centavos — a forma FINANCEIRA
Tolerancia(rel=0.01)                          # 1% por valor — a forma do H-smart-rounding
Tolerancia(abs=0.005)                         # meio centavo
Tolerancia(agg="soma")                        # só realoca o resíduo, sem cortar
Tolerancia(quantum=0.1, agg="soma")           # COMPÕEM: grade E soma exata
```

Três estágios, como as natures: **derivar → aplicar → verificar**. Só que aqui o terceiro é
quem decide — a fórmula *propõe* a precisão, a medição *aceita ou recusa*.

## A tabela

| coluna | pedido | casas | bytes | red% | erro/valor | erro soma |
|---|---|---:|---:|---:|---:|---:|
| `wine.density` | `rel=1%` | 2 | **708** | **93,0%** | 0,503% | 0,02435% |
| `wine.density` | `rel=0,1%` | 3 | 1811 | 82,1% | 0,050% | 0,00027% |
| `wine.density` | `quantum=0,1 + agg` | 1 | 360 | 96,5% | 9,109% | **0,00123%** |
| `wine.density` | `agg="soma"` só | 5 | 10137 | **0,0%** | 0% | 0% |
| `retail.UnitPrice` | `quantum=0,1` | 1 | 2910 | 21,0% | 100% | 0,01389% |
| `retail.UnitPrice` | `quantum=0,1 + agg` | 1 | 3028 | 17,8% | 100% | **0,00037%** |
| `retail.UnitPrice` | `rel=1%` | 4 | 3685 | 0,0% | 0% | 0% |
| `retail.UnitPrice` | `rel=1% down` | 4 | **3701** | **−0,4%** | 0,006% | 0,00011% |

## Cinco leituras

### 1. O `mode` não é só viés — ele muda a fórmula da derivação

Este é o achado do lab, e ele **apareceu como falha**. A literatura destacou o `mode` como o
eixo do **viés** (a distinção do HMRC). Eu derivava a precisão supondo erro de **meio passo**,
que vale para `half-*`. Mas **`down` (truncar) erra um passo inteiro** — nunca sobe.

Resultado: com `rel=1%` e `mode="down"` em `wine.density`, a derivação prometeu 1% e a medição
achou ~1,01%. **A verificação recusou** — que é exatamente o desenho funcionando. A fórmula
agora é ciente do modo (`passo_de_erro`), e a verificação continua sendo o juiz.

### 2. O `rel` é amarrado pela cauda inferior — e isso o inutiliza em money real

Em `retail.UnitPrice`, `rel=1%` deriva **4 casas** — *mais* do que o dado tem. Motivo: existe um
valor de `0,001` na coluna, e 1% dele são `1e-5`. **Um item barato obriga a coluna inteira a
mais precisão**, e o pedido vira no-op.

**Consequência prática**: para dinheiro, o eixo útil é o `quantum` (a grade), não o `rel`. Isso
casa com a norma — a ISO 4217 define *minor unit*, não percentual.

### 3. `agg` sozinho não economiza nada — e está certo

`agg="soma"` em `wine.density`: **10137 B, 0,0% de redução**. Ele mantém a precisão da origem e
só realoca o resíduo — não há o que economizar. O valor dele é o **contrato**, não os bytes.

Onde ele brilha é **composto**: `quantum=0,1 + agg` no `retail.UnitPrice` custa **118 bytes** a
mais que `quantum=0,1` sozinho e derruba o erro da soma de **0,01389% para 0,00037%** — 37×
melhor. Esse é o trade explícito que o parâmetro torna declarável.

### 4. Truncar pode CUSTAR bytes

`rel=1% down` no `retail.UnitPrice`: **3701 B contra 3685** do baseline. Truncar produz valores
menos regulares que o núcleo comprime pior. **Uma perda que aumenta o arquivo** — o FLOOR
nunca-pior seria obrigatório se isto virasse candidato.

### 5. A degradação para lossless é graciosa

`rel=1e-9` deriva 9–11 casas, acima do que o dado tem, e vira **no-op** — o wire fica idêntico
ao baseline e o contrato é cumprido trivialmente. Um pedido absurdamente apertado não quebra:
vira lossless. E `rel=1e-15` (que exigiria >12 casas) e `quantum=0,03` (grade não-decimal)
**recusam**, fail-loud.

## O que muda em relação ao `H-smart-rounding`

O ticket de 2026-04-10 propôs `max_error_pct` — **um eixo**, e presumia que erro é um número.

| o ticket | o que a medição mostrou |
|---|---|
| `max_error_pct=0.001` | `rel` sozinho é inútil em money (a cauda inferior manda) |
| erro é um número | a mesma perda vale 0,5% por valor e 0,024% na soma |
| não tinha `mode` | o modo muda o **bound**, não só o viés |
| não tinha `agg` | é o único eixo que obriga **alocação**, e o único que 3 das 5 áreas exigem |
| — | e a **verificação** é o que impede a fórmula de mentir |

As 4 tarefas do ticket continuam desmarcadas em `src/tcf` — isto é protótipo de lab.

## O que isto orienta

1. **A forma do parâmetro está de pé**: 4 eixos que compõem por AND, um qualificador, três
   estágios, fail-loud. É o conteúdo do `H-LOSS-00` (meta-camada de contrato).
2. **O que ainda não existe é o marcador no wire.** Hoje o laudo é um objeto Python; um dado
   ajustado que viaja sem declarar seu contrato é indistinguível de um exato. Isso é a outra
   metade do `H-LOSS-00`, e é pré-requisito de qualquer weld.
3. **Nenhuma proposta de weld.** O formato segue lossless-puro (decisão do owner, 2026-06-15).
