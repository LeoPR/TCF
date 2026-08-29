---
title: "BUG-VIEW-ORFAO-SEM-MAGIC: a view recusa o wire sem magic que o decode lê, e culpa um legado irrelevante"
status: closed-fixed
priority: P3
severity: "R2 (paridade quebrada em rota documentada, mais mensagem que aponta para a causa errada)"
created: 2026-08-28
updated: 2026-08-28
gate: "correção em src/tcf só com aprovação explícita do owner (I5)"
blocked-by: []
related: [
      src/tcf/view.py,
      src/tcf/decoder.py,
      experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md,
]
---

# BUG-VIEW-ORFAO-SEM-MAGIC

**[probatório → execução]** `encode(..., stamp=False)` emite um wire **sem a linha de
magic**, e essa rota é documentada no `decode`, que a lê. A `view` não a implementa, recusa,
e a mensagem manda o usuário olhar para o legado `#TCF.6`/`#TCF.7`, que não tem nada a ver
com o caso.

Divergência #13 da [auditoria de consistência de
2026-08-27](../experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md),
registrada aqui por não ter ticket próprio. É a menor das três órfãs, e a de conserto mais
barato.

## Repro mínimo

```python
from tcf import decode, encode, view

w = encode(["a", "b"], stamp=False)     # 'a\nb\n'   — sem magic, por opção do chamador

decode(w)          # ['a', 'b']         a rota é documentada e funciona
view(w)            # ValueError: não é #TCF.8M multi-col
                   #              (legado #TCF.6/#TCF.7 cortado, ADR-0032...)
```

O `stamp=False` é kwarg público. Quem o usa está no caminho documentado, e recebe um erro
que fala de outra coisa.

## Causa

A `view` ([`view.py`](../src/tcf/view.py)) decide a família pela linha de magic. Sem magic,
cai no ramo do legado cortado, que é o único outro caso em que a magic falta. O `decode`
tem um ramo a mais, "sem magic, single órfão", que a `view` não replica.

Duas coisas erradas, e vale separar: a **recusa** é uma capacidade que falta, e a
**mensagem** é um diagnóstico errado que existiria mesmo se a recusa fosse a decisão certa.

## Alcance

Nove wires do corpus de paridade. Só alcançável por `stamp=False` explícito; nenhum default
passa por aqui.

## O certo

A `view` implementa o mesmo ramo que o `decode` documenta. Se a decisão for **não**
suportar órfão na camada read-only, então a mensagem tem que dizer isso, e não acusar um
legado que o usuário não usou.

## Critérios de aceite

- [x] `view(encode(["a", "b"], stamp=False))` responde o mesmo que o `decode` para o mesmo
      wire, **ou** recusa com mensagem que nomeia a causa real (`stamp=False` / ausência de
      magic) e não cita `#TCF.6`/`#TCF.7`.
- [x] O caso legado de verdade (wire `#TCF.6`/`#TCF.7`) continua com a mensagem que cita
      ADR-0032, que ali está certa.
- [ ] Os nove wires do corpus de paridade são conferidos por execução. (o corpus de paridade da auditoria vivia no scratchpad de um agente e não foi reproduzido; substituído pelo lab, pelas formas parametrizadas nos testes e pela verificação adversarial de 2026-08-28)
- [x] Lab de evidência em disco (I2), no padrão canônico.
- [x] Suíte completa e gates verdes; sem re-pin.

## Estado

**FECHADO em 2026-08-28 (onda 5).** A saída foi implementar o ramo órfão na `view`, não
só corrigir a mensagem. Custou ~15 linhas porque o mode `blob` já delega os valores ao
`decode` oficial (paridade por construção) e `_n_somado` já conta corpo com RLE (contar LF
erraria em `*3|x`). O critério de família é o mesmo do `decode`: `#TCF.` seguido de dígito
é versionada; qualquer outra coisa é dado órfão. O legado de verdade (`#TCF.6`, `#TCF.7`)
continua com a mensagem que cita ADR-0032; magic sem LF continua "sem shebang".

Mudança de comportamento visível: texto arbitrário sem magic agora **constrói** uma view
(como o `decode` já o lia como órfão); o erro, se houver, sai na materialização.

Evidência: [`2026-08-28-0200-cauda-das-divergencias`](../experiments/lab/dirty/2026-08/2026-08-28/2026-08-28-0200-cauda-das-divergencias/), caso `orfao-sem-magic`.
Testes: `TestViewOrfaoSemMagic` (`test_tcf_lazy.py`): paridade em seis formas (RLE,
quase-magic escapado, `#TCF.x` sem dígito), contagem sem materializar, legado recusado.
