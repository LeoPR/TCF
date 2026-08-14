# Procedência dos dados — e o viés declarado

## Sintético (`sint-money`)

20 preços literais em `run.py`, sem seed. Gravado em `inputs/sint-money.entrada.json` com
`.fonte.json` ao lado.

**Viés, declarado e deliberado**: há um **`0,07` plantado** no meio de valores entre 2,99 e
250,00. Ele existe para amarrar o eixo `rel` — 1% de 0,07 são 7e-4, o que força a coluna
inteira a 3 casas. Sem esse valor eu não veria o comportamento que queria examinar. É um
sintético **construído para exibir um efeito**, não uma amostra de preços.

## Reais

Corpus local `Z:/tcf-data/interim/*.db` (SQLite, read-only). **Não versionado**; o lab roda sem
ele, pulando estas colunas.

| coluna | por que está aqui | n |
|---|---|---|
| `online-retail.online_retail.UnitPrice` | **money real**: 2 casas, e a cauda inferior desce a `0,001` — é onde o `rel` se revela inútil | 2000 |
| `wine-quality.wine.density` | **medida física**: 3–6 casas, faixa estreita (0,987–1,039) — é onde a tolerância tem o que cortar | 2000 |

As duas foram escolhidas por **contraste de regime**, não por representatividade: uma é
dinheiro (grade fixa por norma), a outra é medição (precisão derivada de instrumento). São
exatamente as duas áreas cujas normas o vocabulário precisa cobrir.

**Amostragem**: passo espalhado (`v[::passo]`), alvo 2000. Nunca `LIMIT` puro.

**Viés, declarado:**

- **Duas colunas de duas fontes.** Nada aqui é gate real-world — o gate para qualquer weld
  lossy exige N≥5 fontes mais decisão explícita do owner.
- O resultado mais forte (`wine.density` cai **93%** com `rel=1%`) é **específico do regime**:
  uma coluna de faixa estreita e alta precisão é o melhor caso possível para corte de casas.
  Não generaliza — em `retail.UnitPrice`, o mesmo pedido é **no-op**.
- O `0,001` que trava o `rel` no `UnitPrice` aparece em 4 valores da coluna inteira; é uma
  peculiaridade do dataset (registrada na varredura de float de 2026-08-14), não uma regra do
  varejo. Mas o *mecanismo* que ele exibe — a cauda inferior amarrando o `rel` — é geral.
