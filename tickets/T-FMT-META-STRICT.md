---
title: T-FMT-META-STRICT — decode estrito do meta: o que já fecha por dedução vs o que exige redundância (checksum)
status: open
priority: P3
created: 2026-07-10
updated: 2026-07-10
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-TOOL-TCF-FIX-CORRUPTION.md
  - tickets/T-API-BOUNDARY-CONTRACTS.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
---

# T-FMT-META-STRICT — integridade do meta além do lote 3

**[dispositivo→registro]** Direção do owner (2026-07-10): as sugestões de whitelist são boas —
aplicar agora, **vincular com os outros tratamentos e abrir ticket pra depois**. Este é o ticket.

## Princípio (o eixo do trabalho)

O decode valida por **dedução do cânone**: só aceita o que o encoder emite. Cada regra dessas é
grátis (nenhum byte novo no formato). O que a dedução NÃO alcança é corrupção **geometricamente
consistente** — essa só cai com **redundância** (checksum), que custa bytes e pertence ao trilho
de armazenamento (tcfx/O-FMT-20), não ao wire-format mínimo.

## Já fechado por dedução (welded, T-QA-8 F0 lotes 1-3)

- nome declarado vazio `<size>=` / dangling backslash / hex inválido → erro (lote 1);
- size vs bytes disponíveis + fecho do blob + cross-check n_rows → erro (lote 2; eficácia medida:
  calado-errado 29.2%→3.0% em 1474 cortes);
- whitelist de escape `_ESC_OK = ",=:\\!@%"` — escape de char não-estrutural → erro (lote 3,
  BUG-11b); meta vazio sem body → erro (BUG-08 fold);
- `#TCF.<N≠8>` → erro de versão (lote 2, BUG-04).

## Residuais VINCULADOS (decidir aqui, depois do material comprobatório)

1. **Fusão geometricamente consistente** (BUG-11a residual + BUG-13c): `\` inserido que funde
   tokens OU size-flip cujo consumo total ainda fecha — o caso comum é pego pelo fecho/n_rows
   (medido), o residual é indistinguível de blob legítimo **por construção** → só checksum
   (tcfx/O-FMT-20). NÃO tentar heurística no wire-format.
2. **Flip de NOME no meta** (BUG-13a): renomeia chave calado — idem, só checksum.
3. **nature-id desconhecido no header** (BUG-13b): hoje warning + segue com chave errada;
   candidato a erro estrito pre-1.0 (sem forward-compat a proteger, ADR-0024). Decidir junto com
   a simetria de natures do T-API-BOUNDARY-CONTRACTS.
4. **view sobre blob EOF-truncado** (BUG-13d): candidato "cross-check incremental na
   materialização" (compara len ao materializar a 2ª coluna — custo zero, preserva laziness).
5. **Invariantes internas por modo** (BUG-13e): V2-B `len(stream) % width == 0` + coerência do
   `ntable`; split idem — deduções de graça ainda não aplicadas.
6. **Posição do escape de prefixo**: whitelist atual aceita `\!`/`\@`/`\%` em QUALQUER posição
   (encoder só emite no início) — endurecer é opcional, ganho marginal.
7. **BUG-12** (hang HCC decode sob header corrompido) tem lote PRÓPRIO (toca o CORE), mas o
   guard de progresso é da mesma família: "todo parse válido avança".

## Critério de aceite

- [ ] Pós-material-comprobatório (T-QA-8 F2+), decidir itens 3-6 (cada um red→green, decode-only).
- [ ] Checksum (itens 1-2) especificado no trilho tcfx/O-FMT-20 — NÃO no wire-format mínimo.
- [ ] Toda regra nova = "não-emitível pelo encoder" comprovado (dedução do cânone, nunca heurística).
