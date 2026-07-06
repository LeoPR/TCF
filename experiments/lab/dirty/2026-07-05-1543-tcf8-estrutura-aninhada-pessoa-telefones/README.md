# 2026-07-05 15:43 — TCF.8: estrutura aninhada (pessoa ⊃ telefones) [probatório]

**Auto-contido** (dirty-lab): `structlib.py` (local) + `tcf` (biblioteca; **não toca `src/`**).
`python run.py` regenera tudo. Ticket: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).

> **FOCO: ESTRUTURA, não performance.** O objetivo é organizar **duas tabelas numa estrutura** —
> **dois TCF.8 um após o outro** com um envelope **auto-descritivo** — e provar que **decoda**. Bytes
> são secundários aqui. **Draft v0**: o owner redesenha a sintaxe do envelope.

## Dataset (o teu, mínimo)

`{"nome":"leonardo", "telefones":[{"tel":"(41) 99999-9999"},{"tel":"(41) 99994-9999"}]}`
→ 1 escalar de raiz (`nome`) + 1 array-de-objetos (`telefones`, campo `tel`). = **duas tabelas**.

## Estágios (= a ordem em `artifacts/`)

```
01 ENTRADA         inputs/S4 → 01-entrada-S4-pessoa.json
02 TRADUÇÃO        JSON → 2 tabelas (02-traducao-tabela-{pessoa,telefones}.csv) + árvore (02-traducao-arvore.txt)
03 TCF.8 ANINHADO  cada tabela → 1 bloco TCF.8 (03-tcf8-bloco-{pessoa,telefones}.tcf.txt);
                   os DOIS aninhados um após o outro → 03-tcf8-aninhado.tcf.txt  ← a ESTRUTURA
04 DECODE          desaninha → decoda os 2 blocos → reconstrói o JSON → 04-decode-roundtrip.txt (OK)
```

## A estrutura (draft v0 — `03-tcf8-aninhado.tcf.txt`)

```
#TCF.8-NEST v0
@tree {"order":["nome","telefones"],"root":{"nome":"str"},"arrays":{"telefones":{"tel":"str"}}}
@block root
#TCF.8
leonardo
@block telefones
#TCF.8
(\41) \9999*\9*-\9999      ← OBAT já fatora o (41) 9999…9999; sobra 1\4*3 (o dígito que muda)
1\4*3
```
- `@tree` = **auto-descrição** da árvore (ordem dos campos + tipos + quais são array). É o que torna
  o envelope "TCF.8" (self-describing).
- `@block <nome>` delimita cada **TCF.8** leaf (single-col via `stamp=True`).

## Para REDESENHAR (pontos abertos — teus)

1. **Sintaxe do envelope**: `@tree`/`@block` são placeholders. Podia ser 1 linha só, ou o próprio
   `@tree` ser um TCF, ou marcadores mais enxutos.
2. **Bloco `root`**: escalares da raiz num bloco à parte vs **inline** no header (pra 1 campo, o bloco
   quase não paga).
3. **Link 1:N**: aqui a raiz é única → `telefones` pertence implicitamente. Com N pessoas, precisaria
   de fk/ordenação (é o eixo A-vs-B do lab [1509](../2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/)).
4. **Leaf multi-col**: TCF.8 single-col sai via `stamp`; multi-col hoje cai em TCF.7 (TCF.8 multi só com
   nature). Decidir: leaf multi-col em TCF.7 + tipos no `@tree`, ou estender.
5. **Profundidade**: e se `telefones[i]` tiver um sub-array? (aninhamento recursivo — próximo passo).

## Estado

- **É**: estrutura de 2 TCF.8 aninhados + envelope auto-descritivo, **decoda** (RT OK). Draft pra redesenho.
- **Será**: o owner redesenha o envelope; depois: multi-col leaf, N raízes (fk), aninhamento recursivo.

Convenções: [notas/dirty-lab-convencoes.md](../notas/dirty-lab-convencoes.md).
