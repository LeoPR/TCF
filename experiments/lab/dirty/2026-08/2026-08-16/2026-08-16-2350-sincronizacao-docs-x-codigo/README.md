# 2026-08-16-2350 — sincronização docs × código

## Era / foi / é / será

- **Era**: os docs foram escritos ao longo de ~3 meses, cada um correto no seu momento.
- **Foi**: as revisões de fechamento dos tipos (polaridade, `b2`, lazytype `bB`, weld do
  `.8H`, corte do legado, delimitador de polaridade) mudaram comportamento **e re-pinaram
  os gates de byte** — sem que todos os docs acompanhassem.
- **É**: 23 afirmações dos docs vivos estavam mortas. Corrigidas, e agora **verificáveis
  por execução** (`run.py` → 23/23).
- **Será**: o `run.py` vira a régua re-rodável. Uma afirmação nova que não entre na lista
  segue não-verificada — a seção "NÃO COBERTO" do `RESULTADO.md` declara isso.

## A pergunta

*Cada afirmação que os docs vivos fazem sobre o comportamento do TCF ainda é verdade?*

Não "os docs estão bonitos", e sim: **rodar o código e comparar com o que o doc promete**.

## As duas de maior severidade

1. **[`output-convention.md`](../../../../../../docs/algorithms/output-convention.md)** —
   descrevia um decoder que **skipa `[` e `]`**. Esse skip foi removido em 2026-07-17
   (`BUG-BRACKET-CELL-LOSS`): ele **engolia célula calado**. Quem portasse o formato
   seguindo o doc **reintroduziria perda silenciosa de dado**.
2. **[`core-data-model.md`](../../../../../../docs/algorithms/core-data-model.md)** — é o
   **guia de port pra C/Rust**, e mandava mirar em `D1-D9=1523B, D17a=303B,
   real-world=89616B`. Os três estão mortos há três re-pins. Um port miraria no gate errado
   e falharia sem entender por quê. Vigente: **1545 / 300 / 89430**.

## O padrão que apareceu

As defasagens não são aleatórias — quase todas são de **uma classe só**: o doc congelou na
véspera de um weld. Os quatro welds que mais deixaram rastro:

| weld | data | o que os docs ainda diziam |
|---|---|---|
| ADR-0033 (`.8H` soldado) | 2026-07-14 | "`H` = hierárquico **RESERVADO** → fail-loud" |
| ADR-0034 (header default) | 2026-07-24 | "single-col plano fica **órfão**, 0-byte header" |
| ADR-0035 (polaridade) | 2026-07-26 | wire com `\` de escape em cada slot; gates +41/+207 B |
| ADR-0037/0039 (`b2`, `bB`) | 2026-07-31 / 08-01 | "denso é bool **sem null** por construção"; "união = fail-loud" |

## Como conferir

```bash
python run.py          # -> RESULTADO.md + outputs/ (input + .tcf + roundtrip por caso)
```

Cada caso grava `inputs/<nome>.json`, `outputs/<nome>.tcf` e
`outputs/<nome>.roundtrip.json`. **O diff é o assert** — não há afirmação sem o par
entrada/saída em disco pra terceiro conferir.

## Sobre `src/tcf/`

Três blocos de comentário/docstring foram corrigidos (`__init__.py`, `decoder.py` ×2). São
**comment-only**, e isso foi **provado**, não afirmado: comparação de **AST com as
docstrings removidas** entre `HEAD` e a árvore de trabalho — idêntica nos dois arquivos.
Suíte **1285 passed, 3 skipped**; gates byte-canonical **198 passed**. Nenhum byte de wire
mudou.

## Não coberto (declarado)

- `docs/theory/**` e os blocos **datados** do `STATUS.md` são **log histórico**. Os números
  antigos lá dentro estão *certos* pro momento que registram — não foram tocados.
- `docs/adr/*.md` são **imutáveis** por convenção (`docs/adr/README.md:8-11`). A vigência
  mora no campo Status do **índice**, e esse foi atualizado (11 linhas).
- O verificador prova que as **23 afirmações listadas** batem. Ele **não varre** os docs
  atrás de afirmações novas.

## Conexões

- Mapa que originou o trabalho:
  [`notas/2026-08/2026-08-16-2330-mapa-de-sincronizacao-docs.md`](../../../notas/2026-08/2026-08-16-2330-mapa-de-sincronizacao-docs.md)
- Síntese do mês: [`../../README.md`](../../README.md)
- Índice do dia: [`../INDEX.md`](../INDEX.md)
