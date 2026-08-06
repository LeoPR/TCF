# Plano de fechamento — universo bool/binário/bN (single-col) [plano vigente]

> Aprovado pelo owner 2026-08-01. **Escopo**: single-column. **Régua**: fechar aos poucos cada
> peça do universo bool/binário/bN-geral (elementos que caibam na composição bN + pequenas
> variantes) até termos **cabeçalhos minimalistas e limpos casados com os tipos** — antes da
> etapa int/float e, mais adiante, multi-col (`.8M`/hierárquico: "depois é só ir fechando").

## 1. Já FECHADO neste universo (não retrabalhar)

| peça | ADR | wire |
|---|---|---|
| binário puro (denso b1) | #4b | `#TCF.8b1<n>` |
| ternário (denso b2) | ADR-0037 | `#TCF.8b2<n>` |
| core/RLE com slots | ADR-0038 | `#TCF.8b\n*200|\2` |
| bN de domínio (flat, strings) | ADR-0036 | `#TCF.8B<w><n>` / `C` |
| lazy bool (cabeça congelada + extras) | ADR-0039 | `#TCF.8bB<w><n>` |
| mapa de tipos internos (fonte única) | — | `src/tcf/tipos_internos.py` |

## 2. Triagem dos pendentes (tabela do STATUS)

### A) DESTA etapa (bool/bin/bN, single-col, variantes pequenas)

1. **`T-BN-B64-VALIDATE`** — erro, byte-neutro, **sem lab**: mensagem nível TCF no lugar de
   `binascii.Error`. Aquecimento.
2. **`T-GRAFIA-CHECKLIST`** — processo, byte-neutro: a lição dos 6 incidentes de assimetria
   escapar/desescapar vira **checklist testado** (par injetivo por construção). Blindar antes
   de novos wires.
3. **`T-DENSO-PADDING`** — wire, 1–2 B em ~2/3 dos densos: **lab pequeno + weld**. Padding `=`
   deduzível de `n` e `w` (b1/b2/bN). Cuidado central: decode aceita COM e SEM padding
   (decodável-não-emitido, precedente modo `C`/nomes); emitir sem.
4. **Params de wire** (3 tickets, 1 superfície): `T-BN-LOTE` (modo `C` opt-in) +
   `T-TIPADO-LEGIVEL-PARAM` (nomes legíveis) + `T-FORCAR-MECANISMO-PARAM` (forçar
   RLE/b64/refs). **Um estudo de forma** (kwarg × `PipelineConfig`; precedente: `fallback`/
   `min_len` já são kwargs) e 3 welds pequenos. Os decodes já aceitam as variantes — é
   plumbing de encoder.
5. **`T-MISTO-RLE-B64-SINGLE`** — estudo → talvez weld. Cético por obrigação (derrubada 0/18
   no multi-col): **reality-check real-world primeiro**; sem evidência =
   `closed-insufficient-gain`.

### B) Decisão do owner nesta etapa

6. **`BUG-CHAVE-VAZIA-POSICIONAL`** — fail-loud × preservar `""` via escape (o `.8H` já tem a
   grafia). A rota flat é a única que **altera** dado; cabe no tema "cabeçalhos limpos".

### C) Etapa de INT/FLOAT (próxima, delimitada pelo owner)

`T-BN-TIPADO` (−555/−519 B medidos) · `T-LAZYTYPE-OUTROS` (lazy no `n` + revisão
natures/SPEC) · `T-FLOAT-SLOTS` (precedente bool fixado) · `T-SPEC-L0L1`.

### D) `.9`/CPU (não é desta etapa)

`T-POLARIDADE-FUSE` · `T-GATES-ANTES` · `T-SEQRLE-INCREMENTAL` · `T-OBAT-TRIGRAMA` ·
`T-FEATURES-STREAM` (byte-neutros de CPU) · `T-BN-LARGURA-VARIAVEL` (largura variável =
serialização nova no `bitpack` — **estudo** pode vir antes, weld é `.9`) · `T-BN-GZIP`
(observação, sem ação).

### E) Etapa maior seguinte / decisões transversais

`T-BN-MULTICOL` + decisão bN-dense no FLOOR (⛔ owner) · `T-TIPOS-CONFORTO-MAP` (⛔ owner —
trava tipos novos, não trava esta fila) · `T-MODO-JSON-IMITADOR` (depois da família lazy;
catálogo de alertas já medido no lab 0309).

## 3. A fila (um a um; cada peça no ciclo lab→weld→docs, com aprovação)

1. `T-BN-B64-VALIDATE` — weld direto.
2. `T-GRAFIA-CHECKLIST` — weld direto.
3. `T-DENSO-PADDING` — lab + weld (único que mexe em wire emitido; rota tipada, esperado zero
   movimento nos gates).
4. Estudo de forma dos params → 3 welds (`T-BN-LOTE`, `T-TIPADO-LEGIVEL-PARAM`,
   `T-FORCAR-MECANISMO-PARAM`).
5. `T-MISTO-RLE-B64-SINGLE` — estudo real-world; weld ou fechamento justificado.
6. **Revisão de conformidade de cabeçalhos** (fecho): tabela tipo × wire × header mínimo
   canônico (órfão/stamp/spec/tag/modo) — cada tipo com exatamente uma grafia mínima e
   fail-loud nas não-canônicas. Documento final da etapa.
7. Decisão `BUG-CHAVE-VAZIA` (owner) — encaixar onde cair.

**Gate da etapa**: 1–6 fechados ⇒ universo bool/bin/bN single-col fechado; abrir int/float (C).

## 4. Critério de "universo fechado"

- Fila 1–5 resolvida (welded ou closed-justificado), revisão 6 publicada.
- Tabela tipo×wire×header sem buraco: bool/binário/ternário/strings-k-baixa/lazy — todos com
  header mínimo, uma grafia canônica, fail-loud nas demais.
- STATUS sem nenhum pendente do grupo A aberto.
