# Fechamento do tipo HORA

> **Owner**: *"precisamos fazer testes sintéticos porque campos com hora existem"* ·
> *"seria interessante fechar todos os tipos primeiro até pra ver se o fluxo de spec está
> padronizado e cada um tem suas peculiaridades declaradas, quanto mais coisa em comum melhor."*

**Um tipo não fecha porque compensa — fecha porque foi verificado.**

## Estado — era / foi / é / será

- **Era**: a hora estava **avaliada** (1,03× no único dado real) mas não **fechada**. Faltava o
  que o owner nomeou: os **sintéticos** dos regimes que o corpus não tem, e os **5 eixos**.
- **Foi**: os sintéticos por regime (batimento 15 min/1 min/1 s, expediente, constante), as 9
  bordas contra ISO 8601 / RFC 3339, e a ciclicidade medida em 4 escalas.
- **É**: **0 falhas**. A hora é conforme nos 5 eixos, e tem **7 peculiaridades declaradas** —
  uma delas **corrigindo** o que eu havia registrado. Resultado em [`result.md`](result.md).
- **Será**: datetime é o último. E o spec de hora fica adiado, agora com número.

## A correção que este lab faz

Eu havia registrado que a hora é cíclica e que **isso atrapalha** (o seq-RLE vê um salto
negativo à meia-noite). Medido: **ciclar é repetir**, e o que o seq-RLE perde o **dedup ganha** —
aos 7 dias o wire cíclico é **73,0% menor** que o absoluto. A peculiaridade correta é que a
ciclicidade **troca um mecanismo por outro**, e o `min()` faz a troca sozinho.

## O achado fora de escopo

`nature=SPEC_CPF` numa coluna de horas aplica em **0% dos valores** (`length_wrong` em 96/96) e
**mesmo assim vence o FLOOR** — o wire sai 58 B menor e carimbado `:cpf`. O prefixo `_` uniforme
dos literais vira afixo que o OBAT fatora. RT fecha, então não é corrupção: é **metadado falso**
no campo que serve para dizer o que a coluna é. Registrado como 4ª situação do
`T-NATURE-IGNORADA-CALADA`.

## Por que sintéticos, e o viés que isso carrega

A varredura de 102 colunas confirmou: **hora pura não existe no corpus** — a única parte-hora
vive dentro de um datetime, com segundo constante `00`. Os regimes onde a hora tem
comportamento próprio (telemetria, batimento) **precisam ser construídos**, e são viesados por
construção. Detalhe em [`datasets-provenance.md`](datasets-provenance.md).

## Como rodar

```
python run.py     # sai 0 só se todos os RT fecharem
```

Roda **sem `Z:`** (só a coluna real é pulada). Não toca `src/tcf/`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | o dado e a procedência |
| `outputs/<caso>.tcf` · `.roundtrip.json` · `.meta.json` | wire, contra-prova, procedência |
| `outputs/ciclicidade-<N>dias.{ciclico,absoluto}.tcf` | **o par que mede a ciclicidade** |
| `outputs/ordinal-<N>dias.tcf` | o desenho irmão do `data-iso` |
| `intermediates/eixos.json` · `ciclicidade.json` | as medições, com `CONSTANTE_na_comparacao` |

## Vínculo

`T-HORA-SPEC` · `T-NATURE-IGNORADA-CALADA` (4ª situação, aberta aqui) ·
`data-iso` como gabarito (`src/tcf/natures/data_iso.py`) ·
consolidado dos tipos: [`docs/theory/float-e-variantes-consolidado.md`](../../../../../docs/theory/float-e-variantes-consolidado.md) ·
critério: [`…-0430-fechar-todos-os-tipos-no-08.md`](../../../notas/2026-08/2026-08-14-0430-fechar-todos-os-tipos-no-08.md)
