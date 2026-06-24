# Modelo de dados do CORE — mapa para port (C/Rust)

> **Tipo**: reference [dispositivo de orientação ao port; descreve o código
> canonical de `src/tcf/`, que É a fonte]. Escopo: foco-2 (clareza pra reescrever
> o CORE em linguagem compilada). Companheiro de [OBAT.md](OBAT.md) (camada 1) e
> [HCC.md](HCC.md) (camada 2) — aqueles explicam *o algoritmo*; este fixa as
> *estruturas de dados* que fluem entre os estágios e a **fronteira CORE↔HOST**.

## Por que este doc existe

Um port para C/Rust precisa reproduzir **byte-por-byte** o output do encode
(GATE byte-canonical: D1-D9=1523B, D17a=303B, real-world=89616B — pinados em
`tests/`). Pra isso o port reimplementa só o **CORE** (estruturas + transformações
determinísticas). Tudo que é Python-only (paralelismo, trace de debug, lazy view)
fica de fora sem afetar bytes. Este doc separa os dois e define cada estrutura
com precisão de assinatura.

## Fronteira CORE (portável) ↔ HOST (fica em Python)

| Concern | Onde | Porta? | Nota |
|---|---|---|---|
| OBAT tokenize | `core/online.py` `processar` | **CORE** | LCP/LCS + índice de trigrama |
| HCC tokenize-pieces | `composicional/syntax.py` `_tokenize_pieces` | **CORE** | atomiza tokens em pieces |
| HCC detect | `syntax.py` `_detect_compositions` | **CORE** | aliases (composições) |
| HCC emit | `syntax.py` `_emit_body` (+ `_emit_ref_run`, `_emit_refs_range`) | **CORE** | atribui IDs finais, gera texto |
| seq-RLE post-process | `composicional/hcc_seqrle.py` | **CORE** | `*N+delta\|template` |
| decode | `decoder.py` + `syntax.py` decode + `hcc_seqrle.py` decode | **CORE** | espelho do emit |
| naturezas/SPECS | `naturezas/` (CPF/CNPJ/IP) | **CORE** (opt-in) | encode/decode de valor |
| V2 modos (`!`/`@`/`%`) + min_header | `multi/core.py`, `multi/dict_v2b.py`, `multi/split.py` | **CORE** | decisão por-coluna |
| **paralelismo multi-col** | `multi/parallel.py` (`ProcessPoolExecutor`) | **HOST** | só agenda; cada worker roda o CORE. Serial == paralelo byte-a-byte |
| **trace/rede de debug** | `composicional/_trace.py` | **HOST** | strings de observabilidade; **não afeta bytes** (P2, 2026-06-24) |
| **lazy view** | `view.py` | **HOST** | leitura preguiçosa pós-encode; não participa do encode |

Regra do port: se está em CORE, reproduz exato; se está em HOST, é conveniência
da plataforma — reimplementa do jeito idiomático (threads, sem threads, o que for)
**desde que o byte-output do CORE seja idêntico**.

## Fluxo e estruturas (single-column)

```
strings (list[str], 1 coluna)
   │
   │ dedup preservando 1ª ocorrência → unicas (list[str]); linhas = strings originais
   ▼
OBAT.processar(unicas, min_len) ──► tokens_por_string : list[list[Token]]
   ▼
_tokenize_pieces(linhas, unicas, tokens_por_string)
        ──► pieces_per_line : list[ list[Piece] | None ]
            line_meta       : list[(count:int, eid:int, is_rep:bool)]
            atom_count      : int
   ▼
_detect_compositions(...) ──► alias_to_sub : dict[alias_temp:int → sub:tuple[int,...]]
   ▼
_emit_body(pieces_per_line, line_meta, alias_to_sub)
        ──► body          : list[str]   (uma string por linha lógica)
            prov_to_final : dict[atom_prov_id → final_id]
            alias_to_final: dict[alias_temp  → final_id]
            ref_seqs      : list[list[int]]   (refs por linha, p/ trace)
   ▼
seq-RLE compact_body(body) ──► body' com `*N+delta|template`
   ▼
"\n".join(body') + "\n"   → corpo TCF textual
```

### 1. `Token` (saída do OBAT) — `core/online.py`

Dataclasses (uma lista por string única, na ordem de `unicas`):

- `TokLit(text:str)` — literal puro.
- `TokRefPref(string_id:int, length:int)` — prefixo herdado da string `string_id`
  (**1-based** na ordem de `unicas`), `length` chars do início.
- `TokRefSuf(string_id:int, length:int)` — sufixo herdado, `length` chars do fim.

`string_id` é 1-based. A 1ª string é sempre `[TokLit(s)]`. Refs só apontam pra
strings **anteriores** (online). Índice de trigrama (`s[:3]`/`s[-3:]`) é só
aceleração de busca — não muda o resultado (ver [OBAT.md](OBAT.md)).

### 2. `Piece` (saída do tokenize-pieces) — `syntax.py`

`_tokenize_pieces` quebra os tokens OBAT em **átomos** (frags entre quebras de
linha lógica) e os agrupa em pieces. Cada linha vira `list[Piece]` ou `None`:

- `('lit', text:str, prov_id:int)` — átomo literal; `prov_id` é um **id
  provisório positivo** único (contador `proximo_idx`, atribuído na ordem de
  descoberta).
- `('refs', [prov_id, ...])` — sequência de refs a átomos previamente definidos.
  IDs aqui são **provisórios positivos** nesta fase (átomos herdados por
  prefixo/sufixo apontam o `prov_id` do átomo-fonte).
- `None` — a linha repete um `eid` já emitido (RLE não-adjacente / dict de linha);
  os pieces não são re-gerados, a info vive em `line_meta`.

`line_meta[i] = (count, eid, is_rep)`:
- `count` — multiplicidade do RLE **adjacente** (`*N|` no output).
- `eid` — id 1-based da string única (índice em `unicas` + 1) → vira `^eid` no output.
- `is_rep` — `True` se `pieces_per_line[i] is None` (eid já emitido antes).

### 3. `alias_to_sub` (saída do detect) — `syntax.py`

`_detect_compositions` acha sub-sequências de refs que se repetem e cria
**aliases** (composições). Resultado: `dict[alias_temp → sub]`, onde:

- `alias_temp` — id **temporário positivo** do alias (≥ `atom_count`+algo).
- `sub` — `tuple[int,...]` dos refs que a composição abrevia. **Sinal codifica o
  tipo**: `id > 0` = átomo (prov_id); `id < 0` = referência a outro alias
  (`-alias_temp`, virtual/aninhado). Esta é a **convenção de sinal central** do
  CORE — um port deve preservá-la em todo o pipeline detect→emit.

O detector é guloso/iterativo (net-savings = `(R-1)*(baseline - len_id)`, prune
topK — ADR-0019). O acelerador Cython `_core/detect.pyx` (ADR-0020) é **opcional
e byte-equivalente** ao fallback pure-Python: o port reimplementa a lógica, não
o `.pyx`.

### 4. IDs finais (saída do emit) — `syntax.py` `_emit_body`

O emit faz **uma passada** sobre `line_meta`/`pieces_per_line` e atribui o
**id final** na **ordem do body** (contador `current_id`, incrementa ao emitir
cada átomo novo e cada alias-def). Ou seja: o id final NÃO é o prov_id nem o
alias_temp — é a posição de primeira-emissão. Dois mapas registram a tradução:

- `prov_to_final : dict[atom_prov_id → final_id]`
- `alias_to_final: dict[alias_temp → final_id]`

`ref_seqs : list[list[int]]` guarda, por linha, a sequência de ids finais
referenciados — usado **só** pelo trace de debug (HOST), não pelos bytes.

> **Invariante de port**: a ordem de atribuição de id final é load-bearing.
> Reordenar a varredura muda os números no output → quebra byte-canonical.
> Idem a restrição de body-order dos virtual refs (um alias só pode referenciar
> outro já definido antes — ver `reference_hcc_provas_m5_m8`).

## Gramática do output (marcadores que o emit gera)

Sem brackets, LF only, UTF-8 (ver [output-convention](output-convention.md) e
[TCF-format.md](TCF-format.md)). Marcadores no corpo:

| Marcador | Significado | Origem |
|---|---|---|
| `^eid` | linha = string única nº `eid` (dict de linha / repetição) | `_emit_body` ramo `is_rep` |
| `*N\|<linha>` | RLE adjacente: `N` cópias da linha | `count > 1` |
| `,` | concat efêmero entre dois ref-runs | transição refs→refs |
| `~` | define um alias (composição) inline na 1ª aparição | `_emit_ref_run` (virtual) |
| `A..B` | range de IDs consecutivos (≥3) | `_emit_refs_range` |
| `*` | separador desambiguador (lit\|lit, ref→lit que começa com `,`/`~`, fronteira de dígito) | `_emit_body` |
| `\X` | escape de char literal que colidiria com marcador/dígito | `_escape_lit` |
| `*N+delta\|<template>` | seq-RLE: `N` linhas near-identical, dígitos-escape shiftados por `delta` | `hcc_seqrle.compact_body` |
| `*N+d1,d2,...\|<template>` | seq-RLE multi-delta (per-run) | idem (ADR-0016) |

O `~` é **operador composicional**, não par open/close — ver
`feedback_marcadores_multiplo_proposito`. O decode é o espelho exato: expande
`*N+delta\|` primeiro (hcc_seqrle.decode), depois parseia o corpo HCC.

## Multi-coluna e modos V2 (camada acima do single-col)

`multi/core.py` orquestra N colunas. Header textual:
`#TCF.7` + `M` (multi flag) + linha meta `# <size1>=<name1>,...`. Cada coluna
escolhe um **modo** (decisão por-coluna, byte-driven):

- (sem prefixo) — pipeline HCC normal acima.
- `!` raw (V2-A, ADR-0022) — coluna crua quando HCC não compensa.
- `@` dict (V2-B, ADR-0025) — `multi/dict_v2b.py`, índice base-N de cardinalidade baixa.
- `%` split (ADR-0026) — `multi/split.py`, quebra estrutural; recursa no CORE
  single-col (import lazy `from tcf.multi.core import _encode_multi` pra quebrar
  o ciclo).
- min_header (ADR-0023) — header mínimo quando dá.

`multi/parallel.py` é **HOST**: distribui colunas em processos. O resultado é
byte-idêntico ao serial (`_encode_columns_serial`); o port pode paralelizar como
quiser ou rodar serial.

## Checklist do port (byte-canonical)

1. Convenção de sinal `prov_id>0` / `-alias_temp<0` preservada de detect a emit.
2. ID final = ordem de primeira-emissão no body (não prov nem temp).
3. Body-order de virtual refs respeitada (alias referencia só aliases anteriores).
4. `string_id` do OBAT é 1-based; refs só pra strings anteriores.
5. Separadores `*` emitidos nas mesmas 3 condições (lit\|lit; ref→lit-`,`/`~`;
   fronteira de dígito) — são o que evita ambiguidade no parser do decode.
6. seq-RLE roda **depois** do emit HCC, sobre as linhas de `body`.
7. HOST (parallel/trace/lazy) não entra no byte-output — reimplementar à vontade.
8. Validar contra os snapshots pinados em `tests/test_regression_v1_baseline.py`
   e `tests/test_real_world_snapshots.py`.

## Veja também

- [OBAT.md](OBAT.md), [HCC.md](HCC.md) — os algoritmos das camadas 1 e 2.
- [output-convention.md](output-convention.md), [TCF-format.md](TCF-format.md)
  — gramática textual e header.
- `../adr/0020-*` (Cython opt-in), `../adr/0022/0023/0025/0026-*` (modos V2).
- `../../experiments/lab/dirty/notas/historia-dirty-lab.md` — narrativa M0-M14.
- `src/tcf/` — implementação canonical (a fonte; este doc descreve, não substitui).
