# Um parâmetro de tolerância para float — protótipo

> **Owner (2026-08-14)**: *"vamos refazer um para implementar algo com um parâmetro
> complementar pra float caso a gente queira que ele tenha tolerância. Veja nas nossas
> pesquisas se já fizemos algo assim, acho que sim (testes)."*

**Uma pergunta**: dá para declarar tolerância como parâmetro, **derivar** a precisão dela, e
**verificar** que a promessa foi cumprida?

## Você lembrou certo — e o desenho existia, sem teste

`docs/workbench/_archive/tickets/frozen/H-smart-rounding.md` (2026-04-10, `status: OPEN`)
propôs exatamente isto:

```python
config = EncodeConfig(max_error_pct=0.001, aggregate_columns=["total"])
```

com quatro alternativas, a terceira marcada como *"precisão derivada de tolerância
**(inovação)**"*. **As quatro tarefas do ticket estão desmarcadas** — foi desenhado, nunca
implementado nem testado. Este lab é o primeiro teste, e implementa a terceira alternativa
(as outras caem como casos particulares).

## GATE

**Protótipo de lab, fora de `src/tcf`** — pré-transformação externa, na forma que o `nature=`
já usa. O formato é lossless-puro por decisão do owner (2026-06-15); **nada aqui é proposta de
weld**. O que se testa é a *forma* do parâmetro.

## O contrato deste lab é diferente

O valor muda de propósito, então RT contra a origem não se aplica. Valem três checagens:

1. **o contrato declarado** — cada eixo pedido é medido, e tem de bater;
2. **o formato continua lossless sobre os ajustados** — `decode(encode(x̂)) == x̂`;
3. **fail-loud** — tolerância não realizável **recusa**.

⚠️ Os `.tcf` que não são `.baseline` contêm valores **ajustados de propósito**. O
`roundtrip.json` prova que o formato os preserva — **não** que são os originais. O original
está em `inputs/<coluna>.entrada.json`.

## Estado — era / foi / é / será

- **Era**: `H-smart-rounding` desenhava **um** eixo (`max_error_pct`), e presumia que erro é um
  número. Nunca testado.
- **Foi**: a medição de [`…-2010-perda-propagacao-de-erro`](../2026-08-14-2010-perda-propagacao-de-erro/)
  mostrou que a mesma perda vale 66,67% por valor, 0,00029% na soma e 825,9% numa diferença.
  Um eixo não basta.
- **É**: 12 pedidos × 3 colunas, **0 falhas**. Resultado em [`result.md`](result.md).
  `wine.density` com `rel=1%` cai **93%**; e o `mode` mostrou mudar a **fórmula**, não só o viés.
- **Será**: falta o **marcador no wire** — hoje o laudo é um objeto Python, e um dado ajustado
  que viaja sem declarar seu contrato é indistinguível de um exato. É a outra metade do
  `H-LOSS-00`.

## O defeito que o lab pegou em mim

Eu derivava a precisão supondo erro de **meio passo**, o que vale para `half-*`. **`down`
(truncar) erra um passo inteiro.** Com `rel=1%` e `mode="down"` em `wine.density`, a derivação
prometeu 1% e a medição achou ~1,01% — e a **verificação recusou**, em vez de entregar dado
violando o contrato que ele mesmo declara. Corrigido em `passo_de_erro()`.

Isso é o desenho funcionando: **fórmula que não é verificada mente**, e foi a terceira vez
nesta sessão que essa mesma classe apareceu.

## Como rodar

```
python run.py     # sai 0 só se todo pedido cumprir o que promete (ou recusar)
```

Roda **sem `Z:`** (as colunas reais são puladas; a sintética basta para ver a mecânica).

## Onde olhar

| arquivo | o que é |
|---|---|
| `tolerancia.py` | o protótipo: `Tolerancia`, `deriva_casas`, `aplica`, `verifica` |
| `inputs/<coluna>.entrada.json` · `.fonte.json` | **os originais** e a procedência |
| `outputs/<coluna>.baseline.tcf` | o wire sem tolerância |
| `outputs/<coluna>.<pedido>.tcf` · `.roundtrip.json` · `.meta.json` | o wire ajustado |
| `intermediates/laudos.json` | **o laudo de cada pedido**, com os 3 estágios e os checks |

## Vínculo

`H-LOSS-00` (meta-camada de contrato — este é o conteúdo dela) · `H-LOSS-01` (maior resto) ·
`H-LOSS-03` (round, o PoC de junho) · **`H-smart-rounding`** (o desenho de 2026-04-10) ·
[`loss-taxonomia.md`](../../../notas/2026-06/loss-taxonomia.md) ·
nota [`…-2010-perda-propagacao-de-erro`](../../../notas/2026-08/2026-08-14-2010-perda-propagacao-de-erro.md) ·
lab irmão: [`…-2010-perda-propagacao-de-erro`](../2026-08-14-2010-perda-propagacao-de-erro/)
