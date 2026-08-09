# Resultado — revisão dos tipos: nada fora do lugar, e dois ganhos que ninguém pediu

**2026-08-09 · dirty · 32 casos (28 comportamento + 4 fail-louds), RT verde em todos,
rotas e tetos conferidos. Matriz completa em [`outputs/matriz.md`](outputs/matriz.md).**

O ciclo mexeu em muita coisa — bN de domínio, denso b1/b2, índice interno, lazytype,
nB tipado, SPEC_DATA_ISO, fix do FLOOR, fix do None, e ontem o seq-RLE periódico no corpo
que **todas** as rotas usam. A revisão percorreu cada família contra o comportamento
esperado. Veredito: **está tudo certo** — cada tipo roteia pra onde deve, faz RT, e os
fail-louds falam alto.

## O quadro por família

| família | casos | estado |
|---|---|---|
| bool (b1 · b2 · core-slots · lazytype · null) | 5 | ✓ rotas e bytes como soldado |
| numérica tipada (nB · sequencial · **periódico** · grafia) | 7 | ✓ — e a rota tipada **já herda o ADR-0040** (`#TCF.8n`, `*200~10,10,10,50\|`, 33 B) sem weld extra |
| strings (bN · true/false-string · high-card · vazia) | 4 | ✓ caixa preservada; vazio/whitespace sobrevivem |
| natures (CPF · CNPJ · IP · +null) | 4 | ✓ FLOOR-vê-bN e fix do None valendo |
| data (7 regimes) | 7 | ✓ válvula, null e grafia-suja se comportam |
| fail-louds (`date` · `Decimal` · `datetime` · misto) | 4 | ✓ todos falham alto com a mensagem certa |

## Os dois achados positivos (efeitos do ADR-0040 que ninguém pediu)

**1. O `mensal` INVERTEU — o spec agora aceita.** Antes do periódico, o candidato ordinal
do mensal perdia do ISO (deltas 28–31 quebravam o `*N+d|` em pares) e o spec **recusava**
a coluna (1085 B). Com o período p=12, o candidato ordinal venceu:
`#TCF.8 :data-iso` · **679 B** (1,6×). Exatamente a inversão que o lab `0042` previu —
realizada de graça pelo weld, sem mexer na nature.

**2. CNPJ constante: a nature GANHA (e minha nota esperava recusa).** Com 40 CNPJs
idênticos, eu esperava o RLE de linha do core vencer com o literal cru. A nature venceu
(`#TCF.8 :cnpj`, 25 B): o payload transformado (14 dígitos → 12 sem pontuação, DV
regenerado) é menor **por valor**, então o MESMO RLE de linha comprime um template menor.
A nota da matriz estava errada; o comportamento está certo — e é o FLOOR fazendo o que
promete: comparar wires completos, não intuições.

## Interação do periódico — antes (lab `0042`) × agora

| caso | antes | agora | |
|---|---:|---:|---|
| data-diaria | 32 | **32** | intocado (uniforme continua dele) |
| data-uteis | 1590 | **40** | 39,8× |
| data-uteis-feriado | 1889 | **677** | 2,8× |
| data-mensal | 1085 | **679** | 1,6× — **spec recusava, agora aceita** |
| ids-turno | 1959 | **32** | 61,2× |

## Miúdos que valem registro

- `data-com-ruido` (4 lixos em 600 úteis) = **148 B**: cada lixo quebra o run periódico,
  mas os pedaços entre quebras seguem comprimindo — degradação proporcional, não colapso.
  `data-com-null` idem (147 B) via slot 0.
- `data-grafia-suja` (`2026-1-5` / `2026/01/05` / `20260105`): o spec recusa a coluna
  inteira (nenhuma parseia canônica) e o **bN pega o low-card** (62 B). A válvula e o
  FLOOR compõem.
- `cpf-com-null` = 45 B via bN — o fix do None (que estourava `TypeError` nas 4 natures)
  segue de pé no caminho composto.
- O delta-coluna (`T-DATA-ALVO-DELTA`, não soldado) continua com o que pegar: nos regimes
  de ciclo **quebrado** o periódico faz 677–679 B onde o delta-coluna hipotético fazia
  345–349 B. A complementaridade medida no `0042` está intacta.

## Conclusão

Nenhum problema encontrado; a matriz sai com código 0 e fica como **conformidade
re-executável** (rota + RT + teto por caso). A suíte (1238) já cobre as famílias em
profundidade; esta matriz cobre a **largura** — todos os tipos, lado a lado, com os wires
de vitrine em `outputs/`.
