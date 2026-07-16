---
title: T-FMT-META-STRICT — decode estrito do meta: o que já fecha por dedução vs o que exige redundância (checksum)
status: open
priority: P3
created: 2026-07-10
updated: 2026-07-12
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

## Residuais VINCULADOS

1. **Fusão geometricamente consistente** (BUG-11a residual + BUG-13c): `\` inserido que funde
   tokens OU size-flip cujo consumo total ainda fecha — o caso comum é pego pelo fecho/n_rows
   (medido), o residual é indistinguível de blob legítimo **por construção** → só checksum
   (tcfx/O-FMT-20). NÃO tentar heurística no wire-format.
2. **Flip de NOME no meta** (BUG-13a): renomeia chave calado — idem, só checksum.
3. ~~**nature-id desconhecido**~~ — **FEITO 2026-07-10 (lote 4)**: ValueError em decode
   (multi+single) e view; revoga o forward-compat de 2026-06-24 (testes re-pinados).
4. ~~**view EOF-truncado**~~ — **FEITO 2026-07-10 (lote 4)**: cross-check incremental na
   materialização (`_col` compara len com coluna já cacheada; laziness intacta).
5. ~~**Invariantes internas por modo**~~ — **FEITO 2026-07-10 (lote 4)**: V2-B ntable bound +
   stream%width + índice∈tabela (byte de editor virava índice NEGATIVO e wrapava calado);
   split ntmpl bound; `_dict_parts` da view em paridade.
6. **Posição do escape de prefixo**: whitelist atual aceita `\!`/`\@`/`\%` em QUALQUER posição
   (encoder só emite no início) — endurecer é opcional, ganho marginal.
7. **BUG-12** (hang HCC decode sob header corrompido) tem lote PRÓPRIO (toca o CORE), mas o
   guard de progresso é da mesma família: "todo parse válido avança". Destino vigente: 0.8.1,
   depois do fechamento do núcleo `.8` (T-REL-08, decisão do owner 2026-07-12).
8. **Orçamento defensivo de expansão**: counts RLE/seq-RLE, ranges e cadeias composicionais de
   blob não-canônico podem solicitar saída desproporcional antes de qualquer cross-check final.
   Registrar limites/contabilidade (`max_rows`, bytes/frags ou contrato equivalente) antes do 1.0,
   mas **não inserir limite arbitrário no wire-format durante o closeout `.8`**: o encoder pode
   produzir runs legítimos grandes. Quando abrir implementação, desmembrar ticket próprio com
   contrato de API + testes de count zero/negativo/gigante, range inválido e expansão acumulada.

## Achado 2026-07-16 — KeyError cru no decode flat de blob estrangeiro (CORPO, não meta)

**[probatório]** Achado lateral da verificação adversarial dos registros de direção (workflow
`wf_154282a3`), reproduzido em execução: `decode('abc123')`, `decode('x9')` e
`decode('#TCF.8\nabc123')` vazam **`KeyError: 123`/`KeyError: 9` crus** — linha de corpo terminada
em dígitos NÃO-escapados é parseada como ref HCC inexistente e a exceção sobe sem re-tipagem.
O encoder nunca emite isso (dígito final sai escapado `\123`), então é a mesma doutrina deste
ticket: blob estrangeiro deve falhar **tipado** (ValueError "ref inválida/blob corrompido?"), não
com KeyError — mesma família dos re-tipados do F0 (lote 3) e do hardening `.8H` (UnicodeDecodeError,
`int()` leniente). **Não consertado** (toca `src/tcf`, exige aprovação); regra candidata: resolução
de ref fora do range de nodes → erro tipado, "não-emitível pelo encoder" comprovado.

## Critério de aceite

- [x] Itens 3-5 executados (lote 4, 2026-07-10; red→green, decode-only, 590 passed).
- [ ] Checksum (itens 1-2) especificado no trilho tcfx/O-FMT-20 — NÃO no wire-format mínimo.
- [ ] Item 6 decidir pós-material; BUG-12 em lote 0.8.1; item 8 vira ticket próprio pré-1.0.
- [ ] Toda regra nova = "não-emitível pelo encoder" comprovado (dedução do cânone, nunca heurística).
- [ ] Achado 2026-07-16 (KeyError cru em ref inexistente de blob estrangeiro) re-tipado quando o
      owner aprovar mexer no decode flat.
