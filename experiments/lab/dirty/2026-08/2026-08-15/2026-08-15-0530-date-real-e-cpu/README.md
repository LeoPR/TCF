# Date em dado REAL — as transformações sobrevivem? E quanto custa o `min()` ampliado?

> **Owner (2026-08-15)**: *"pode seguir"* — sobre medir em dado real e a CPU do `min()`
> ampliado, as duas ressalvas que o lab anterior deixou declaradas.

Par de fechamento do [`…-0400-date-processo-de-compressao`](../2026-08-15-0400-date-processo-de-compressao/).
Aquele mediu 6 transformações em 14 regimes **sintéticos** e terminou com duas ressalvas
explícitas. **Este lab existe para fechá-las** — e uma delas se fechou contra o lab anterior.

## O gap que este lab fecha

1. **tudo era sintético** — e o precedente é duro: o `T-DATA-ALVO-MENSAL` deu **95% em sintético
   e 0,0% em real**;
2. **CPU não foi medida** — um `min()` de 6 candidatos custa tempo.

## Estado — era / foi / é / será

- **Era**: uma partição limpa em 14 regimes sintéticos, com o `delta2` como achado principal
  (esparsa-ordenada, 3854 → 605 B).
- **Foi**: levar as 6 transformações para as colunas de data do corpus, com **predição declarada
  antes da medição** — sem isso, "o `delta` ganhou em 3 colunas" é indistinguível de pescaria.
- **É**: **`componentes` vence nas 7 colunas embaralhadas** (51,9–55,1% sobre o ordinal welded) e
  é estável a ordem *e* a amostragem; **`delta` vence na única coluna real já ordenada**
  (`football-date`, **71,0%**, em ordem física). **O `delta2` não venceu uma única vez em 24
  medições.** O `min()` ampliado custa **+47,7% a +86,1%** de encode. Resultado em
  [`result.md`](result.md).
- **Será**: o protocolo de transformação de coluna — agora com preço e ganho medidos em dado
  real, não só sintéticos.

## A disciplina que este lab acrescenta

**Predição declarada antes da medição.** Medir 6 transformações em N colunas e depois escolher a
melhor não prova nada. O lab classifica o regime primeiro, **declara** o que a partição
sintética prevê, e só então mede. O que vale é a taxa de acerto.

E **dois pares de contra-prova**, porque sete das oito colunas previram a mesma coisa — o que
testaria uma célula da partição, não a partição:

| bloco | o que isola | veredito |
|---|---|---|
| **1b** — as mesmas colunas **ORDENADAS** | só a **ordem** muda | a predição mudou em 7/8 — não é carimbo; 4/8 acertos |
| **1c** — as mesmas colunas **CONTÍGUAS** | só o **modo de amostrar** muda | minha predição foi **refutada** (0/8 viraram), e o resultado ficou mais forte |

Placar do classificador nos três blocos: **18 de 24**, com as 6 falhas todas errando na mesma
direção — **subestimam o `delta`**. Diagnóstico no [`result.md` §4](result.md).

## O erro de método que o Bloco 1c corrige

Eu amostrei com passo espalhado (`v[::300]`) — a convenção do projeto. Mas `lineitem` está
ordenada por `l_orderkey` e as datas de um pedido são próximas, então **passo 300 pula sempre
para outro pedido**: o \|Δ\| mediano medido foi **710** contra **50** na coluna inteira.

**Para transformações que leem vizinhos, o passo espalhado não é uma amostra — é uma
transformação dos dados.** A conclusão não mudou (o `componentes` vence nas duas amostragens),
mas a régua precisa mudar, e isso não vale só para o date.

## Como rodar

```
python run.py     # sai 0 só se toda transformação fechar o RT pela sua inversa
```

**Precisa de `Z:/tcf-data/interim/`** (corpus, não versionado). Sem ele, as colunas são puladas
e o lab não mede nada. `src/tcf` intocado: as transformações são funções de coluna importadas do
lab `…-0400`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `run.py` | os 4 blocos, com a regra de predição **inalterada** desde a 1ª rodada |
| `inputs/<col>.entrada.json` · `.fonte.json` | a coluna e a procedência, com a classificação declarada |
| `inputs/<col>-ORDENADA.*` · `<col>-CONTIGUA.*` | os dois pares de contra-prova |
| `outputs/<col>.<transf>.tcf` | **o wire de cada candidato**, isolado |
| `outputs/<col>.spec-welded.tcf` · `.roundtrip.json` | o que o TCF emite hoje |
| `outputs/INDEX.md` | a tabela navegável |
| `intermediates/cpu.json` | a CPU, com o `AVISO` de dev-run e a `REGUA` histórica |
| `resultado.json` | tudo, incluindo `falhas: []` |

## Vínculo

[`…-0400`](../2026-08-15-0400-date-processo-de-compressao/) (o lab que este fecha) ·
`T-DATA-ALVO-DELTA` (pede o protocolo de coluna) · `T-DATA-ALVO-MENSAL` / `T-CORPUS-DATA-MENSAL`
(o precedente 95% sintético → 0,0% real, que **se repetiu no `delta2`**) ·
`T-CANDIDATO-SEM-DEDUP` (a régua de +84–93% de CPU) · `T-DATA-GRAFIAS-IRMAS` (as 2 grafias reais
fora deste lab) · `T-DATA-LAZY-ISO` (o ordinal welded) · `T-SEQRLE-PERIODICO` (ADR-0040)
