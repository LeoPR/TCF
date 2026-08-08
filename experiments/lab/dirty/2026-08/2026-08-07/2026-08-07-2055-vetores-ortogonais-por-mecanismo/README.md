# Vetores ortogonais por mecanismo — encode × decode

**2026-08-07 · dirty · first-order**

```
python run.py     # regenera inputs/, outputs/, intermediates/
```

## Pergunta

Todo weld recente fechou com *"encolheu N bytes"*. Bytes é a âncora — é o vetor mais justo
pra decidir — mas tratar os outros como nota de rodapé esconde **troca vestida de ganho**.

> Quando um mecanismo aumenta a compressão, ele é **win-win** ou é **troca**? Se for troca,
> não existe "melhor de tudo" — existe melhor **para uma condição**.

## Os quatro vetores, e o que é novo

| vetor | como | estado no repo |
|---|---|---|
| **bytes** | tamanho do fio | já medido em todo lab |
| **CPU** | mediana de 12 rep × 4 rodadas **intercaladas entre variantes** | `bench_perf` faz melhor |
| **memória** | pico `tracemalloc`, decode | `bench_perf` tem sondas heap/rss |
| **online-ness** | de quanto do fio o valor `j` **depende** | **não existe** — nenhum grep por `first_byte`/`streaming` acha nada em `bench_perf` |

## Atribuição — comparar com a alternativa, não com o default

Cada dataset vira 4 variantes que isolam o mecanismo:

```
core       magic + corpo do core (sem polaridade, sem bN)
+pol       core + camada de borda de polaridade
+bN(B)     bN modo B — domínio primeiro
+bN(C)     bN modo C — domínio por último
```

A diferença entre variantes **é** o custo do mecanismo. Não é comparação com `encode()`
(que já escolheu por `min()`).

## Como a online-ness é medida — e as duas tentativas que falharam

Dois métodos **construtivos**, cada um no seu domínio:

- **truncamento** — menor `decode(wire[:p])` que já dá o valor `j` certo. Usa o decoder
  real; prova de suficiência, não estimativa. Serve pro core e pra polaridade.
- **extração aritmética** — no bN modo `B` truncar não serve (a checagem de tamanho exato
  do b64 recusa fio curto: é o **código** sendo estrito, não o formato sendo sequencial).
  O valor sai de cabeçalho + domínio + 1 quarteto, conferido contra o `decode`.
- **estrutural** — modo `C`: o domínio vem depois do payload. 100% por construção.

Duas abordagens foram escritas e jogadas fora antes; o cabeçalho de
[`dependencia.py`](dependencia.py) explica por quê (resumo: um leitor mínimo correto **é**
o decoder; e mutação de cauda dá 100% em tudo porque invalida o fio, não o valor).

## Regra de leitura: sinal ≠ magnitude

CV de ±14% a ±24% nesta máquina. **O sinal é confiável** quando a direção se repete nas 4
rodadas intercaladas; **a magnitude não é**. Medindo em rodadas separadas (o jeito errado),
o mesmo fenômeno deu +86%/+60%/+37%/+11%. O lab marca `INDEFINIDO` quando o sinal troca.

Magnitude publicável vem do `bench_perf`, com calibrador e gate térmico.

## Resultado

Em [`result.md`](result.md). Em uma linha: **o bN é troca favorável** (ganha bytes, CPU e
memória; perde latência do 1º valor, ganha acesso aleatório) e **a polaridade é troca ruim
no caso que a expõe** (−1 byte por +25–42% de CPU), com o agravante de que o critério de
hoje decide por byte e **não consegue nem ver** o custo.

## Arquivos

- [`run.py`](run.py) — as medições e o relatório · [`dependencia.py`](dependencia.py) — os
  métodos de online-ness
- [`outputs/medicoes.md`](outputs/medicoes.md) — tabelas por caso ·
  [`intermediates/medicoes.json`](intermediates/medicoes.json) — cru
- `outputs/*.tcf` — os 19 fios medidos · `inputs/*.json` — os datasets

`src/tcf` **não é tocado**.
