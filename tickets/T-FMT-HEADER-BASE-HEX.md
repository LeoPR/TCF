---
title: T-FMT-HEADER-BASE-HEX — Base HEX implícita dos byte-sizes do header (decimal só como comando de inspeção/IO)
status: decided-weld-gated
priority: P2
created: 2026-07-09
updated: 2026-07-09
gate: pre-1.0
blocked-by: []
related:
  - tickets/T-OPT-INFERENCE.md
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - tickets/T-FMT-TCF8H-HEADER.md
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - experiments/lab/dirty/notas/bases-radix-usos-tcf.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
---

# T-FMT-HEADER-BASE-HEX — base HEX implícita dos byte-sizes do header

**[dispositivo]** Ticket **super-específico** de UM sítio de radix: o **byte-size de cada coluna no header**.
Escopo estreito de propósito (owner 2026-07-09): fechar o **processo** do ganho imediato, sem esperar a
otimização geral de bases (essa é gradual — ver o [registro de bases/radix](../experiments/lab/dirty/notas/bases-radix-usos-tcf.md)).
Desmembrado do [T-OPT-INFERENCE](T-OPT-INFERENCE.md) Item 1.

## Decisão (owner 2026-07-09)

**HEX é a base DEFAULT e IMPLÍCITA dos byte-sizes do header.** O size é armazenado em hex, sem marcador; o
arquivo se auto-explica **por convenção** (`len(hex(s)) ≤ len(str(s))` sempre → win-or-tie vs decimal).

**Decimal NÃO é um formato alternativo** — é uma **opção de apresentação**, acessível só por **comando
explícito**, para três usos e nada mais:
1. **Legibilidade / inspeção** — um viewer/CLI renderiza o header em decimal pra humano ler.
2. **Declarar em entrada/saída** — a API pode aceitar/emitir decimal na fronteira (contrato explícito).
3. **Debug / controle nosso** — durante desenvolvimento.

Como hex é **ganho puro**, não há razão pra manter decimal como base *armazenada*: o blob no disco/fio é
**sempre hex**; decimal vive só na borda (IO), no inspetor e no debug.

## O processo (o que importa agora — otimização vem depois)

1. **Armazenado = hex sempre** (minúsculo, sem zeros à esquerda → canônico, round-trip exato:
   `int(h,16)` reconstrói o size, re-encode dá o mesmo literal).
2. **Colisão-livre**: o alfabeto hex `[0-9a-f]` é disjunto dos separadores do meta (`, = : { } [ ] \n`) —
   não quebra o parse "lê size até o separador". (É a razão de hex e não base-94/87 aqui: base-94 inclui
   os separadores; a base máxima colisão-livre fica pro modo byte-máximo-sob-contrato, estudo gradual.)
3. **Comando de decimal** (apresentação): flag no viewer/decode (`--decimal` / inspeção) e opção na API pra
   declarar decimal em IO. Não altera o blob.
4. **Rede de dedução** (segurança, se algum dia houver blob decimal legado/declarado sem marca):
   (a) letra `[a-f]` num size → HEX inequívoco; (b) split decimal não fecha o body → HEX; (c) all-digit
   ambíguo → **default HEX**. Invariante: **um arquivo, uma base**.

## Compatibilidade (princípio do owner 2026-07-09)

Estamos em **desenvolvimento**: retrocompatibilidade com `#TCF.6`/`#TCF.7` (sizes decimais) é **só
comparativo evolutivo**. **No fechamento do 1.0 TUDO do passado fica obsoleto e morre — vive só no histórico
do git.** O design-alvo **NÃO terá `if .7` / `if .6`**: hex-default é *a* forma; decimal-armazenado é legado
que não sobrevive ao 1.0. Durante o dev, trocar a base = **re-pin de baselines** (ADR-0024, git-as-compat) —
os pins byte-canônicos (D1-D9, real-world) são baseline de comparação, não contrato imutável pré-1.0.

## Escopo — SÓ o byte-size do header

Este ticket fecha **apenas** a base do byte-size do header. Os outros sítios de radix (índices `@dict`
base-94, `bN` bits, refs OBAT/HCC decimais, `^N`, ref-stream…) estão **catalogados** no
[registro de bases/radix](../experiments/lab/dirty/notas/bases-radix-usos-tcf.md) e serão estudados/fechados
**aos poucos** — cada um no seu ticket, quando pagar.

## Weld (gated — implementação, não coberta por "concluir a decisão")

Sítios exatos (survey `tcf-radix-survey`, file:line verificados):
- **emit**: `multi/core.py:230,234` (`f"{len(b)}…"` → `f"{len(b):x}…"`).
- **parse**: `multi/core.py:349,357` (`int(size_str)`→`int(_,16)`) **E** `view.py:99,104` (o lazy
  RE-parseia o size independente — mudar os dois em **lockstep**, senão o `view()` quebra; o survey pegou).
- **NÃO tocar** os estimadores de largura de ref `n_est`/`len(str(id))` (`syntax.py:328-329,354`): são dos
  refs do CORPO, que ficam **decimais** (hex ali colide com o digit-escape — ver registro de bases balde C).
- **Pin que move**: **D17a** (303B, multi-col, re-pinável ADR-0024/0025). **Real-world NÃO move** (snapshots
  single-col não têm meta de size). Canônico garantido no ENCODE (`:x` = minúsculo/sem-zero); `int(_,16)` é
  leniente, então a canonicidade se impõe no emit, não no parse.

Exige: **go explícito do owner p/ `src/tcf`** + re-pin D17a + suite verde. É a etapa de implementação; a
DECISÃO/processo acima está concluída. Mapa completo dos outros sítios de base:
[registro de bases/radix](../experiments/lab/dirty/notas/bases-radix-usos-tcf.md).

## Critério de aceite

- [x] Decisão registrada: hex-default implícito armazenado; decimal só comando (inspeção/IO/debug).
- [x] Processo definido: canônico round-trip, colisão-livre, comando-decimal, rede de dedução, uma-base.
- [x] Princípio de compat registrado (passado morre no 1.0; sem `if .N`; re-pin em dev).
- [x] Vinculado nos docs que falam da base (T-OPT-INFERENCE, checklist C4, O-FMT-18, omit-contract, registro de bases).
- [ ] (weld) go do owner p/ `src/tcf` + re-pin baselines + suite verde — **etapa de implementação, gated**.
