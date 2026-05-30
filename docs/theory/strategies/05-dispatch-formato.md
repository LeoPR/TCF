---
title: Dispatch, Multi-Column, PipelineConfig & Format Inventory
type: reference
parent: strategies-map
subsystem: dispatch-formato
---

# Dispatch, Multi-Column, PipelineConfig & Format Inventory

**Como decide caminhos**:
**ENCODE DISPATCH:** encode(data, nature=, nature_per_col=, layers=cfg, parallel=, side_outputs=) -> isinstance(data, list[str]) ? YES: [CAMADA 0 optional] if nature: apply encode_value() per value -> _encode_column(data, header='val', side=side, cfg=cfg) [single-col pipeline M10, returns body puro, no shebang] | NO: isinstance(data, dict) ? YES: [CAMADA 0 optional] if nature_per_col: apply encode_value() per col per value -> _encode_multi(data, side=side, parallel=parallel, cfg=cfg) [multi-col pipeline, returns #TCF.6 M + meta + bodies] | NO: raise TypeError | SINGLE-COLUMN PIPELINE (_encode_column): _encode_column(values, header, side=None, cfg=DEFAULT_PIPELINE) -> Dedup via OrderedDict (preserve first occurrence) | [CAMADA 1: Pre-Pass] if cfg.pre_pass: analyze_column(values) -> ColumnFeatures | detect_cadence_from_features(features, unicas) -> (cadence_detected, cadence_info) [Regra 1: uniform_length + high LCP+LCS; Regra 2: numeric + high_card] | detect_min_len_from_features(features) -> min_len in {3,4,5,6} [decision tree: n_threshold=100 gating, avg_len/card/is_numeric branches] | [CAMADA 2: OBAT Tokenization] -> if cadence_detected AND cfg.obat_shape_preserve: processar_with_hint(unicas, min_len=min_len, prefer_shape_consistency=True) [tries to preserve shape across consecutive strings] else: processar(unicas, min_len=min_len) [canonical OBAT: greedy best pref+suf via LCP+LCS, trigram-indexed] -> tokens_por_string, obat_log | [CAMADA 3: HCC Compaction] -> if cfg.hcc_seq_rle: syn = HCCSeqRLE() else: syn = M8AVirtualRefsSyntax() | body = syn.encode(values, unicas, tokens_por_string, header) [M8A: tokenize pieces, detect compositions, emit body with refs/atoms/aliases; M10: post-process body lines, detect near-identical runs, emit '*N+delta|' markers] | [Side Outputs] if side is not None: populate: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes | return body (text, always ends with \\n) | MULTI-COLUMN PIPELINE (_encode_multi): _encode_multi(table, side=None, parallel=, cfg=DEFAULT_PIPELINE) -> Validate: non-empty, uniform row counts, no ',' or '=' in col names | Stringify values (NULL -> '') | Dispatch: parallel flag + len(table) >= 2 ? YES (parallel=True|int AND len >= 2): _encode_columns_parallel(table_str, want_side, n_workers=N, cfg) [order cols by workload desc, submit to ProcessPoolExecutor, collect via as_completed, reorder by original dict order] -> col_bodies_bytes, per_col_sides | NO: _encode_columns_serial(table_str, want_side, cfg) [iterate in dict order, call _encode_column per col] -> col_bodies_bytes, per_col_sides | Build multi header: meta_pairs = \",\".join(f\"{len(b)}={name}\" for name, b in col_bodies_bytes) | header = b'#TCF.6 M\\n# ' + meta_pairs.encode() + b'\\n' | Byte-precise concat: body_concat = b''.join(b for _, b in col_bodies_bytes) | full = header + body_concat | [Side Outputs] if side is not None: multi_info: {n_rows, n_cols, total_bytes, header_bytes, body_bytes, parallel_workers} | per_col: dict[name, SideOutputs] | return text = full.decode('utf-8') | DECODE DISPATCH: decode(tcf_text, nature=, nature_per_col=) -> tcf_text.startswith('#TCF.6 M') ? YES: _decode_multi(tcf_text) -> dict[str, list[str]] | [CAMADA 0 optional] if nature_per_col: apply decode_value() per col per value | NO: _decode_column(tcf_text) -> list[str] | [CAMADA 0 optional] if nature: apply decode_value() per value | return result (dict or list) | SINGLE-COLUMN DECODE (_decode_column): _decode_column(tcf_text) -> syn = HCCSeqRLE() | syn.decode(tcf_text) -> list[str] [HCCSeqRLE.decode: expand '*N+delta|' markers first, then M8A decode] | return values | MULTI-COLUMN DECODE (_decode_multi): _decode_multi(tcf_text) -> Find line 1 (shebang): validate MAGIC_MULTI | Find line 2 (meta): validate META_PREFIX, parse 'size1=name1,size2=name2,...' | For each (size, name) pair: -> slice body[cursor:cursor+size] (byte-precise) | _decode_column(body_text) -> list[str] | result[name] = list[str] | cursor += size | return result (dict[str, list[str]]) | HCC M8A ENCODE (M8AVirtualRefsSyntax.encode): encode(linhas, unicas, tokens_por_string, header) -> Phase A: _tokenize_pieces(linhas, unicas, tokens_por_string) | collect breaks (QB quotient positions) | for each unique value: decompose into lit/ref pieces | pieces_per_line, line_meta (count, eid, is_rep), atom_count | Phase B: _detect_compositions(pieces_per_line, atom_count) | iterative: count sub-tuplas K>=2, apply virtual-relaxed filter, pick highest net=(R-1)*(baseline-n_tam), substitute, next iter | returns alias_to_sub, iter_traces | Phase C: _emit_body(pieces_per_line, line_meta, alias_to_sub) | walk pieces, emit lits (escape digits, *, \\, ~), emit refs (M1.E ranges + ~ composition) | emit aliases (inline-expanded chains with pairwise binarization) | body: list[str], prov_to_final, alias_to_final, ref_seqs | Build debug info (trace, rede) | return body text: '\\n'.join(body) + '\\n' | HCC M10 ENCODE (HCCSeqRLE.encode): encode(linhas, unicas, tokens_por_string, header) -> body_text = super().encode(...) (M8A) | body_lines = body_text.rstrip('\\n').split('\\n') | compact_body(body_lines) | detect_seq_runs: consecutive pairs with same escape-digit runs + consistent delta list | for each run: emit '*N+delta|template' (or '*N+d1,d2,...|' for mixed) | collect info: start_line, end_line, count, deltas, savings | return compacted_lines, info_list | return text: '\\n'.join(compacted) + '\\n'

### Estrategias (27)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **Dispatch Strategy (encode)** | decision-point | [src/tcf/encoder.py:53-114](../../../src/tcf/encoder.py) | data type check, nature/nature_per_col specs (optional), layers (PipelineConfig), parallel flag | encode() called with any data |
| **Dispatch Strategy (decode)** | decision-point | [src/tcf/decoder.py:52-91](../../../src/tcf/decoder.py) | _MULTI_MAGIC_STR = '#TCF.6 M' | decode() called with TCF text |
| **Single-Column Encode Pipeline (M10 Canonical)** | estrategia | [src/tcf/encoder.py:117-178](../../../src/tcf/encoder.py) | cfg.pre_pass (bool, default True), cfg.obat_shape_preserve (bool, default True), cfg.hcc_seq_rle (bo | dispatch determines list[str] input OR _encode_multi calls for each column |
| **Multi-Column Encode Router** | estrategia | [src/tcf/multi.py:40-111](../../../src/tcf/multi.py) | parallel: False (serial default), True (os.cpu_count workers), int N >= 1 (N workers); cfg: Pipeline | encode() called with dict[str, list[str]] |
| **Parallel Encoding Strategy (Work-Stealing)** | estrategia | [src/tcf/multi.py:131-182](../../../src/tcf/multi.py) | n_workers computed from parallel flag; heuristic: sum(len(v) for v in col) per column | parallel=True\|int and len(dict) >= 2 in _encode_multi |
| **Multi-Column Decode Router** | estrategia | [src/tcf/multi.py:195-234](../../../src/tcf/multi.py) | none (pure parser) | decode() detects #TCF.6 M prefix |
| **Nature Pre-Transform Filter (CAMADA 0, opt-in)** | filtro | [src/tcf/encoder.py:97-99 (list), 103-109 (dict)](../../../src/tcf/encoder.py) | nature: TemplatedCheckedSpec \| None (list); nature_per_col: dict[str, TemplatedCheckedSpec] \| None | nature/nature_per_col params provided to encode() |
| **Pre-Pass Cadence Detection (Regra 1 + 2)** | heuristica | [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py) | n_sample=5 (default, tunable), threshold=0.7 (LCP+LCS ratio), numeric_card_threshold=0.5 | cfg.pre_pass=True in _encode_column |
| **Min-Len Auto-Detection (Heuristic v3)** | heuristica | [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py) | n_threshold=100 (gating), avg_len, cardinality, is_numeric from ColumnFeatures | cfg.pre_pass=True in _encode_column |
| **OBAT Shape-Preserve Hint** | heuristica | [src/tcf/obat_shape.py:32-120](../../../src/tcf/obat_shape.py) | last_shape: (p_src, p_len_old, has_L, s_src, s_len_old) \| None, min_len constraint | cadence_detected=True AND cfg.obat_shape_preserve=True |
| **HCC Detector (M8A Unified Atom+Virtual)** | estrategia | [src/tcf/composicional/syntax.py:225-362](../../../src/tcf/composicional/syntax.py) | atom_count (# atomics from tokenization), virtual-count filter (<=1), position-order constraint | HCCSeqRLE.encode or M8AVirtualRefsSyntax.encode after tokenization |
| **HCC Seq-RLE Near-Identical Compaction** | estrategia | [src/tcf/composicional/hcc_seqrle.py:150-227](../../../src/tcf/composicional/hcc_seqrle.py) | delta: int (M10 compat) or list[int] (ADR-0016), escape-digit run positions detected via find_escape | cfg.hcc_seq_rle=True after HCC M8A body generation |
| **Escape Literal Encoding** | helper | [src/tcf/composicional/syntax.py:53-73](../../../src/tcf/composicional/syntax.py) | text string, reserved: {*, \, ~, digit} | every literal in M8A _emit_body |
| **Ref-Run Composition Emission** | helper | [src/tcf/composicional/syntax.py:470-542](../../../src/tcf/composicional/syntax.py) | refs: list (mixed int > 0 for atoms, int < 0 for virtuals), state dict (current_id, prov_to_final, a | M8A emit phase for every refs piece |
| **PipelineConfig Toggle pre_pass** | threshold | [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py) | pre_pass: bool = True | cfg passed to _encode_column |
| **PipelineConfig Toggle obat_shape_preserve** | threshold | [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py) | obat_shape_preserve: bool = True | cfg in _encode_column OBAT dispatch (line 149-156) |
| **PipelineConfig Toggle hcc_seq_rle** | threshold | [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py) | hcc_seq_rle: bool = True | cfg in _encode_column HCC dispatch (line 159-162) |
| **Side Outputs Capture Container** | marcador | [src/tcf/side_outputs.py:27-51](../../../src/tcf/side_outputs.py) | all fields initialized to None/empty | side_outputs param provided to encode() |
| **Format Marker: Shebang** | marcador | [src/tcf/multi.py:36, src/tcf/decoder.py:49](../../../src/tcf/multi.py) | MAGIC_MULTI = b'#TCF.6 M', checked via startswith() | Every multi-col encode, every decode dispatcher |
| **Format Marker: Meta Line** | marcador | [src/tcf/multi.py:36-37, 95-96](../../../src/tcf/multi.py) | META_PREFIX = b'# ', format: 'size1=name1,size2=name2,...', validators: no ',' or '=' in names | Every multi-col encode output, every multi-col decode parse |
| **Format Marker: RLE Count Prefix** | marcador | [src/tcf/composicional/syntax.py:462-465, 747-751](../../../src/tcf/composicional/syntax.py) | N: count as int, separator: '\|' | M8A _emit_body or _decode when count > 1 |
| **Format Marker: Seq-RLE Near-Identical (M10)** | marcador | [src/tcf/composicional/hcc_seqrle.py:202-210](../../../src/tcf/composicional/hcc_seqrle.py) | N: count, delta: int \| list[int], template: first line of run | cfg.hcc_seq_rle=True after HCC body generation |
| **Format Marker: Atomic Reference Ranges (M1.E)** | token-type | [src/tcf/composicional/syntax.py:91-101](../../../src/tcf/composicional/syntax.py) | consecutive threshold=3, separator: '..' for range, ',' between units | M1.E composition chain emission, _emit_refs_range |
| **Format Marker: Composition Chain (M1.E)** | token-type | [src/tcf/composicional/syntax.py:104-114](../../../src/tcf/composicional/syntax.py) | separator: '~' for pairwise composition, ranges via '..' | M8A _emit_composition and _emit_ref_run |
| **Format Marker: Ref-Body Separator** | token-type | [src/tcf/composicional/syntax.py:434-453](../../../src/tcf/composicional/syntax.py) | separators: '*' (disambiguate lit/ref), ',' (ref continuation), term_seq flag | M8A emit_body phase for every piece transition |
| **Format Marker: Virtual Alias Reference** | token-type | [src/tcf/composicional/syntax.py:413-418, 755](../../../src/tcf/composicional/syntax.py) | prefix: '^', ID: 1-indexed into nos_decl array | M8A emit when is_rep=True (second+ occurrence of unique value) |
| **Reserved Characters (All Layers)** | categoria | [src/tcf/natures/templated_checked.py:34, src/tcf/composicional/syntax.py:65](../../../src/tcf/natures/templated_checked.py) | _RESERVED = {\n, \r, \t, space, ',', '~', '*', '\\', '#', '=', '[', ']', '<', '>', '"', '\'', '`', ' | All encoding paths (literals, nature values) |

### Detalhamento

**`Dispatch Strategy (encode)`** (decision-point, [src/tcf/encoder.py:53-114](../../../src/tcf/encoder.py))  
Top-level dispatch via isinstance(data, dict). If list[str], calls _encode_column with default header='val'; if dict, delegates to _encode_multi (which routes to multi-col pipeline). Raises TypeError for other types. Nature pre-transform (CAMADA 0, opt-in) applied BEFORE pipeline if nature= or nature_per_col= provided.

**`Dispatch Strategy (decode)`** (decision-point, [src/tcf/decoder.py:52-91](../../../src/tcf/decoder.py))  
Routing via shebang prefix check. If tcf_text.startswith('#TCF.6 M'), calls _decode_multi (dict result); else calls _decode_column (list result). Nature reverse-transforms applied post-decode if nature/nature_per_col provided.

**`Single-Column Encode Pipeline (M10 Canonical)`** (estrategia, [src/tcf/encoder.py:117-178](../../../src/tcf/encoder.py))  
Core unit _encode_column orchestrates CAMADA 1-3: (1) Pre-pass: analyze_column + detect_cadence (rules 1-2 ADR-0008) + detect_min_len (heur v3 ADR-0010) IF cfg.pre_pass=True, else cadence=False, min_len=3 default; (2) OBAT tokenization: processar_with_hint(prefer_shape_consistency=True) if cadence detected AND cfg.obat_shape_preserve=True, else canonical processar; (3) HCC: HCCSeqRLE (M10) if cfg.hcc_seq_rle=True else M8AVirtualRefsSyntax (M9). Side outputs captured per-column into provided SideOutputs container.

**`Multi-Column Encode Router`** (estrategia, [src/tcf/multi.py:40-111](../../../src/tcf/multi.py))  
Orchestrates dict->TCF serialization: validates (non-empty, uniform row counts, no ',' or '=' in col names), stringifies all values (NULL->'' per ADR-0013), chooses serial vs parallel dispatch based on parallel flag + column count (>= 2), encodes each column to body bytes, builds meta line '# size1=name1,size2=name2,...', outputs magic + meta + byte-precise concat.

**`Parallel Encoding Strategy (Work-Stealing)`** (estrategia, [src/tcf/multi.py:131-182](../../../src/tcf/multi.py))  
Fase 1b (2026-05-24): Orders columns by workload descending (sum bytes per col as proxy), submits to ProcessPoolExecutor via as_completed (dynamic work-stealing), reorders results by original dict order for byte-identical output. Enabled only if parallel=True/int AND len(table) >= 2 (overhead rule). Serial fallback for 1-col or parallel=False.

**`Multi-Column Decode Router`** (estrategia, [src/tcf/multi.py:195-234](../../../src/tcf/multi.py))  
Parses shebang + meta line (finds 2 newlines, validates MAGIC_MULTI + META_PREFIX), splits meta into (size, name) pairs, byte-precise slices body, decodes each via _decode_column, assembles dict result. No reordering needed (serial decode preserves order).

**`Nature Pre-Transform Filter (CAMADA 0, opt-in)`** (filtro, [src/tcf/encoder.py:97-99 (list), 103-109 (dict)](../../../src/tcf/encoder.py))  
ADR-0015 pre-pass filter: if nature= or nature_per_col= provided, applies encode_value() per value BEFORE pipeline M10. Caller must provide spec out-of-band to decoder. Templated+Checked+Unique (CPF/CNPJ) compresses valid IDs to base-94, literals prefixed '_'. Marker: _ prefix distinguishes encoded vs literal fallback. Opt-in per-column (dict) or global (list).

**`Pre-Pass Cadence Detection (Regra 1 + 2)`** (heuristica, [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py))  
Two-rule heuristic (ADR-0008): Regra 1 (wrapper+counter) — uniform lengths in first n_sample strings + LCP+LCS / length >= threshold (default 0.7) in consecutive pairs; Regra 2 (numeric high-card) — is_numeric=True AND cardinality > 0.5. Returns (bool, info_dict with rule_hit, reason, details). Drives obat_shape_preserve hint decision.

**`Min-Len Auto-Detection (Heuristic v3)`** (heuristica, [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py))  
Decision tree (ADR-0010 H-DA-11): if n_rows < 100 return 3 (gating, preserves M9 baseline exactly); else: card < 0.2 -> 3; avg_len >= 25 -> 6; avg_len >= 8 && card >= 0.4 -> 6; avg_len >= 5 && is_numeric && card >= 0.8 -> 6; avg_len >= 12 && card >= 0.7 -> 5; avg_len >= 3 && card >= 0.2 -> 4; else 3. Achieves 99.5% oracle match on Adult+TPC-H.

**`OBAT Shape-Preserve Hint`** (heuristica, [src/tcf/obat_shape.py:32-120](../../../src/tcf/obat_shape.py))  
Conditional optimization (ADR-0009): if prefer_shape_consistency=True AND last_shape exists, tries to replicate (p_src, p_len, has_L, s_src, s_len) shape on next string via _try_preserve_shape. Exact match: LCP >= p_len && LCS >= s_len; Wider fallback: reduce lens to available; Greedy fallback (canonical _escolher_par) if both fail. Preserves byte-canonical (shape replication deterministic given LCP/LCS contract).

**`HCC Detector (M8A Unified Atom+Virtual)`** (estrategia, [src/tcf/composicional/syntax.py:225-362](../../../src/tcf/composicional/syntax.py))  
Iterative composition detector (unlimited iterations, stops when no net > 0 candidate). Counter sub-tuplas K>=2 with R>=2, applies virtual-relaxed filter (<=1 virtual; if virtual at pos>0, alias must be resolved before sub's first emission), scores baseline_chars - estimated_id_chars, picks highest net=(R-1)*(baseline-n_tam). Per iteration: allocates alias_temp, substitutes in pieces, continues. Outputs alias_to_sub dict, iter_traces for debugging.

**`HCC Seq-RLE Near-Identical Compaction`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:150-227](../../../src/tcf/composicional/hcc_seqrle.py))  
Post-process body lines via detect_seq_runs (consecutive pairs pass compare_for_seq): same length + same escape-digit run positions + all diffs within runs + consistent delta list. For uniform delta (all equal, non-zero), emits M10-compat '*N+delta|template'; for mixed deltas (per-run), ADR-0016 '*N+d1,d2,...|template'. Expands on decode via expand_seq_marker. Detects runs greedily (consume maximal consecutive matches). Savings: sum(len(line_k)+1 for k in run) - (len(marker)+1).

**`Escape Literal Encoding`** (helper, [src/tcf/composicional/syntax.py:53-73](../../../src/tcf/composicional/syntax.py))  
Escapes reserved chars in literals: digits -> \d (run of digits escaped together), special chars *, \, ~ -> \ prefix. Returns (escaped_text, term_seq_flag) where term_seq=True if line terminates with escaped digit run (prevents confusion with ref-mode digit parsing in decoder).

**`Ref-Run Composition Emission`** (helper, [src/tcf/composicional/syntax.py:470-542](../../../src/tcf/composicional/syntax.py))  
Emits mixed atom/virtual ref runs: atomic segments -> M1.E ranges (a..b if 3+ consecutive), joined by ','; virtuals -> _emit_alias (def or use). Alias first-emission: inline-expands sub (linear chain), pairwise binarization allocates K-1 IDs, unresolved inner aliases gain final IDs at completion positions. Recursive expansion + body-order validation ensures correct final ID assignment.

**`PipelineConfig Toggle pre_pass`** (threshold, [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py))  
Boolean toggle (default True). When True, runs analyze_column + detect_cadence_from_features + detect_min_len_from_features in CAMADA 1 pre-pass. When False, skips all heuristics: cadence_detected=False, min_len=3 (M9 default). Allows M9 baseline restoration for ablation studies.

**`PipelineConfig Toggle obat_shape_preserve`** (threshold, [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py))  
Boolean toggle (default True). When True AND cadence_detected, uses processar_with_hint(prefer_shape_consistency=True) instead of canonical processar. Shapes on consecutive strings to reduce HCC detection burden. False forces canonical OBAT regardless of cadence.

**`PipelineConfig Toggle hcc_seq_rle`** (threshold, [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py))  
Boolean toggle (default True). When True, uses HCCSeqRLE (M10 with seq-RLE post-process). When False, uses M8AVirtualRefsSyntax (M9 pure, no seq-RLE). Controls whether near-identical run compaction via '*N+delta|' markers is applied.

**`Side Outputs Capture Container`** (marcador, [src/tcf/side_outputs.py:27-51](../../../src/tcf/side_outputs.py))  
Optional reciprocal container (dataclass, all fields Optional). Per-column: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes. Multi-col: multi_info (n_rows, n_cols, total_bytes, header_bytes, body_bytes, parallel_workers), per_col dict. Populated only if side_outputs= provided (overhead=0 if None, logs discarded). Enables consumption by schema_builder, EncodeManager, debug tools.

**`Format Marker: Shebang`** (marcador, [src/tcf/multi.py:36, src/tcf/decoder.py:49](../../../src/tcf/multi.py))  
Multi-column magic: '#TCF.6 M' (8 bytes) followed by newline. Dispatches decoder to multi-col path. Single-column has NO shebang (body puro). Exact string comparison startswith() in decode dispatcher.

**`Format Marker: Meta Line`** (marcador, [src/tcf/multi.py:36-37, 95-96](../../../src/tcf/multi.py))  
Second line: '# size1=name1,size2=name2,...' (space after '#', CSV-like col descriptor). Parsed by splitting on ',', then each pair on '=' (size is byte count as int, name is col name). Names cannot contain ',' or '='. Enables byte-precise body slicing on decode.

**`Format Marker: RLE Count Prefix`** (marcador, [src/tcf/composicional/syntax.py:462-465, 747-751](../../../src/tcf/composicional/syntax.py))  
Repeat-length encoding (M8A + M10): '*N|value' emitted when consecutive identical values appear (count N >= 2, single values emit bare). Parser regex: line.startswith('*') && '|' in line, extracts count via int(line[1:bar]). Byte-preserving: N counted as decimal string. Decode re-emits [value] * N.

**`Format Marker: Seq-RLE Near-Identical (M10)`** (marcador, [src/tcf/composicional/hcc_seqrle.py:202-210](../../../src/tcf/composicional/hcc_seqrle.py))  
Extension of RLE for near-identical runs. M10-compat format: '*N+delta|template' (uniform delta) or ADR-0016 '*N+d1,d2,...|template' (per-run deltas). Delta sign explicit: +/- prefix ('+' omitted if >=0, implicit for <0). Decoder distinguishes via ',' in delta portion.

**`Format Marker: Atomic Reference Ranges (M1.E)`** (token-type, [src/tcf/composicional/syntax.py:91-101](../../../src/tcf/composicional/syntax.py))  
Range compression for atomic refs: 3+ consecutive IDs -> 'a..b' (single/pair -> bare IDs '1,2'). Ranges separated by ','. Used in composition chains and ref-run emission. Decoder expands 'a..b' via range(a, b+1).

**`Format Marker: Composition Chain (M1.E)`** (token-type, [src/tcf/composicional/syntax.py:104-114](../../../src/tcf/composicional/syntax.py))  
Chain of atomic IDs (pairwise composition via binarization): '1~2' (pair), '1~2~3' expands to intermediate '4=(1~2), 5=(4~3)'. Ranges apply: '1..3~4' = '1~2~3~4'. Separator '~'. Decoder reconstructs pairwise: frags[a+b], then frags[result+c], etc.

**`Format Marker: Ref-Body Separator`** (token-type, [src/tcf/composicional/syntax.py:434-453](../../../src/tcf/composicional/syntax.py))  
Transition separators in body: lit->lit: '*'; lit->ref: optional (if ref starts with ',' or '~'); ref->lit: '*' if lit terminates digit (prevents ref-mode parser consuming digit as continuation); ref->ref: ',' (inline). Detects term_seq flag from _escape_lit. Decoder: ',' continues ref expression, '*' terminates.

**`Format Marker: Virtual Alias Reference`** (token-type, [src/tcf/composicional/syntax.py:413-418, 755](../../../src/tcf/composicional/syntax.py))  
Caret prefix for repeated unique values: '^N' (single emit, bare ID), '*N|^N' (repeated emit N times). Used to reference earlier-emitted unique string without re-tokenization. Decoder: finds nos_decl[N-1].

**`Reserved Characters (All Layers)`** (categoria, [src/tcf/natures/templated_checked.py:34, src/tcf/composicional/syntax.py:65](../../../src/tcf/natures/templated_checked.py))  
Complete reserved set (format vocabulary, no user literals allowed): { *, \, ~, ,, #, =, [, ], <, >, ", ', `, _, \n, \r, \t, space }. Nature encoder uses BASE94 (94 chars from ASCII 33-126 minus reserved). M8A escape routine handles *, \, ~ via \ prefix; digits via \d (run).

### Notas


EXHAUSTIVE FORMAT INVENTORY:

SHEBANG (Line 1, multi-col only): '#TCF.6 M' (8 bytes) + newline. Dispatch decision in decode(). Absent in single-col.

META LINE (Line 2, multi-col only): '# size1=name1,size2=name2,...' (space after '#'). Parsed: split ',' then '=' (once per pair). Constraints: names cannot contain ',' or '='. Size=byte count of body. Order matches dict.

BODY (Lines 3+):
- Single-col: sequence of HCC-encoded line values
- Multi-col: column bodies concatenated byte-precise (no separators)

LINE ENCODING (HCC Output):
- RLE marker (M8A+M10): '*N|value' (N>=2). Decimal count, separator '|'
- Seq-RLE marker (M10): '*N+delta|template' or '*N+d1,d2,...|template'. M10-compat uniform or ADR-0016 mixed per-run
- Atomic ref range (M1.E): 'a..b' (3+ consecutive), '1,2,3' (bare). Threshold=3, separator='..'
- Composition chain (M1.E): '1~2' (pairwise), '1~2~3' (chained). Decoder reconstructs pairwise
- Virtual alias ref (M8A): '^N' (single), '*N|^N' (repeated). 1-indexed into nos_decl
- Literal text (M8A, escaped): digits '\\d' (run), special '\\*' '\\\\' '\\~'. term_seq=True if ends with \\d
- Ref-body separators (M8A): '*' (lit-to-lit, lit-to-ref if starts with ',' or '~', ref-to-lit if starts digit or term_seq), ',' (ref-to-ref)

RESERVED CHARACTERS (all layers): {*, \\, ~, ,, #, =, [, ], <, >, \", ', `, _, \\n, \\r, \\t, space}. Total 19 (18 printable + whitespace). BASE94 uses 50+ remaining. Marker '_' (MARKER_LITERAL) distinguishes nature-encoded vs literal.

BACKWARD COMPAT: M9 (no seq-RLE) fully readable as M10 subset. cfg toggles allow selective M9. Old pre-ADR-0013 multi without shebang not auto-detected. Brackets '[' ']' skipped for back-compat.

SIDE OUTPUTS FIELDS (optional): Per-col: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes. Multi-col: multi_info, per_col dict.

CRITICAL BYTE-CANONICAL PATHS: (1) Dedup OrderedDict.keys() order, (2) Dict iteration order + parallel reorder, (3) OBAT tie-break > strict, (4) HCC detector Counter order + net tie-break, (5) M1.E threshold=3, (6) Seq-RLE greedy consume, (7) Shape preservation exact->wider->canonical, (8) Composition pairwise left-to-right.

WHAT EACH SUBSYSTEM EMITS: CAMADA 0 (Nature): '_' prefix marker. CAMADA 1 (Pre-pass): cadence_info, min_len. CAMADA 2 (OBAT): tokens, log. CAMADA 3a (M8A): body with *, |, ^, ~, ,, ranges. CAMADA 3b (M10): '*N+delta|', '*N+d1,...|'. Multi wrapper: '#TCF.6 M', '# size=name,...', parallel_workers.

PINCH POINTS FOR V2: Nature (new categories inherit protocol), OBAT (shape preservation fallback chain), HCC (detector subclass), Multi-col (meta line delimiters), Side outputs (new Optional fields).


---
