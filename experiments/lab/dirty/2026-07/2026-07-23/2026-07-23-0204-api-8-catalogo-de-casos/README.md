# 2026-07-23-0204 — Catálogo de casos da API `.8` (pós-Passo 2)

Um exemplo de **cada situação de dispatch** da API única `encode`/`decode`, com input · wire
`.tcf` · roundtrip · debug (SideOutputs + leitura de header), pra **inspeção do comportamento de
saída** (header, marcadores, tipos, telemetria). Não é sobre volume — synthetic pequeno e
determinístico.

**Ticket/refs**: contrato de dispatch [`docs/reference/api.md`](../../../../../../docs/reference/api.md) ·
[T-CODE-TCF8H-JSON-PARITY](../../../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) ·
[ADR-0033 §emenda](../../../../../../docs/adr/0033-hierarchical-codec-weld.md) · Passo 2 (commit `e855f1c`).

## Estado

- **era**: os exemplos de comportamento estavam espalhados na suíte de testes (asserts), sem um
  lugar pra o owner *olhar a saída* de cada caso lado a lado.
- **foi/é**: um catálogo executável — `run.py` gera, pra cada caso, o `.tcf` real + o roundtrip
  diffável + um dump de debug, e consolida em `result.md`.
- **será**: base pra inspecionar regressões de header/wire ao longo do `.9` (é só re-rodar e
  diffar `outputs/`).

## Como rodar

```
python run.py        # regenera inputs/ outputs/ intermediates/ + result.md
```
`python` precisa achar `tcf` — o `run.py` já insere `<repo>/src` no path. Roundtrip esperado:
**22 OK, 0 falhas** (C4/C5/C6 são fail-loud *esperados*, não contam como roundtrip).

## Layout

- **`result.md`** — o catálogo pra leitura: por caso, input → wire → header explicado → roundtrip.
- **`inputs/<id>.{json,csv}`** — a entrada (extensão real; CSV pro caso de fonte tabular).
- **`outputs/<id>.tcf`** — o wire REAL, byte-a-byte, inspecionável.
- **`outputs/<id>.roundtrip.json`** — `decode(wire)`, pra diffar contra o input.
- **`intermediates/<id>.debug.txt`** — header + SideOutputs (hier_info, multi_info, per_col,
  nature_apply, hcc_trace) por caso.

## Grupos de casos

| grupo | cobre |
|---|---|
| **SINGLE** (S1–S4) | list[str] → órfão (0 B header) · RLE de linha `*N|linha` · version-stamp `#TCF.8\n` · nature CPF (FLOOR compete) |
| **MULTI** (M1–M4) | dict[str,list[str]] → `#TCF.8M` · marcadores `!`raw/`@`dict/`%`split · sizes HEX · `min_header`/`fallback` off · `sort_by`+`drop_names` (transformação, RT por idempotência) · nature CNPJ por-coluna |
| **HIER** (H1–H7) | `#TCF.8H` — dataset (list[dict]) · objeto `#O` · escalar `#V` · vazios `#D0`/`#E`/`#D2` · tipos preservados (int/float/bool/null) · aninhado profundo · nature CPF em folha aninhada |
| **CONTRATO** (C1–C6) | Passo 2 type-coherent: `[1,2,3]`→array tipado · None preservado · ragged→objeto · **fail-loud**: union misto · tuple não-JSON · kwarg flat no `.8H` |
| **FONTES** (F1) | MESMO dado via CSV (plano→`#TCF.8M`) vs JSON aninhado (→`#TCF.8H`) — wires diferentes |
| **COMPRESSÃO** | `.tcf` vs gzip/brotli/zstd (sinal qualitativo, **não** é TCF) |

## O que observar

- **Header por rota**: sem-header (single órfão) · `#TCF.8M<meta>` (hex, marcadores) · `#TCF.8H`
  (dataset direto, ou `#D`/`#E`/`#O`/`#V`) · `#TCF.8\n` (stamp) · `#TCF.8 :cpf` (nature single).
- **Tipos**: no `.8H` o decode devolve o TIPO EXATO (`30`≠`"30"`, `True`≠`"true"`, `None`≠`""`).
- **FLOOR das natures**: só entra `:id` na coluna onde a nature-transformada é MENOR (never-worse).
- **Fail-loud**: union/tipo-não-JSON/kwarg-incoerente falham ALTO com mensagem que ensina —
  em vez de stringificar ou ignorar calado (os deslizes que o Passo 2 eliminou).
