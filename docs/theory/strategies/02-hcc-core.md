---
title: HCC (Hierarchical Compositional Coding) M8.A — Camada 2 (Compactação Composicional)
type: reference
parent: strategies-map
subsystem: hcc-core
---

# HCC (Hierarchical Compositional Coding) M8.A — Camada 2 (Compactação Composicional)

**Como decide caminhos**:
**Fluxo de Decisão HCC M8.A (3 Fases Sequenciais)**:

**FASE A — Tokenize (_tokenize_pieces linhas 151-221)**:
1. Input: linhas (strings com RLE), unicas (unique strings), tokens_por_string (OBAT)
2. _rle_adjacente(linhas) -> (string, count) groups
3. For each group: eid = unica_to_eid[string]
4. IF eid in eid_emitido -> is_rep=True, skip pieces emit, append line_meta(count, eid, True)
5. ELSE -> tokenize: fragments + refs herança via _coletar_quebras + quebras tracking
6. Merge 'ref' pieces consecutivos, output pieces_per_line[li] = [('lit'|'refs', ...), ...]
7. Output: pieces_per_line, line_meta, atom_count

**FASE B — Detect (_detect_compositions linhas 225-362)**:
1. WHILE TRUE (max 99 iterações):
   a. Count all K>=2 sub-tuplas em ref sequences, track sub_first_line[sub]
   b. Track alias_first_line[alias] para virtuals já em corpo
   c. Build candidates: sub com R>=2 E (0 virtuals OR (1 virtual AND (pos=0 OR alias_first_line<sub_first_line)))
   d. Compute net = (R-1)*(baseline - n_tam) para cada candidato
   e. PICK best_net > 0 (tie: Counter order)
   f. IF best is None -> STOP
   g. ELSE -> alias_temp++, alias_to_sub[alias_temp] = list(sub), substitute all sub in pieces_per_line com -alias_temp
2. Output: alias_to_sub, iter_traces

**FASE C — Emit (_emit_body linhas 391-468)**:
1. For each line_meta (count, eid, is_rep):
   a. IF is_rep -> emit `*count|^eid` (or `^eid` if count=1)
   b. ELSE:
      i. prov_to_final mapping inicializa para atoms desta linha
      ii. For each piece ('lit'|'refs'):
         - 'lit': current_id++, prov_to_final[idx]=current_id, emit _escape_lit(text) + possibly `*` separator
         - 'refs': emit _emit_ref_run(refs) com segment recursivo via _emit_alias
      iii. Track prev_lit_term_digit pra decidir `*` separator próxima piece
2. Output: body (list de linhas texto), prov_to_final, alias_to_final, ref_seqs (traced)

**Decisões-chave Detector**:
- **net > 0**: accepta candidate iff lucro > 0 (absolute)
- **virtual constraint**: rejeita se 1 virtual em pos>0 e ordem violated
- **R >= 2**: rejeita sub com <2 ocorrências
- **max 99 iterations**: safety limit
- **Greedy tie-break**: Counter insertion order (primeiro encontrado ganha, não max-multiple)

**Decisões Emit**:
- **Prev_type + prev_lit_term_digit**: decide `*` separator
- **is_rep**: ^eid vs recompile
- **Pairwise left-assoc**: chain flattening order-determinístico
- **Inline expansion**: virtuals em pos 0 garantido resolvível

### Estrategias (24)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **Atomic refs** | marcador | [src/tcf/composicional/syntax.py:3-5, 26-28](../../../src/tcf/composicional/syntax.py) | prov_id >= 1; final_id alocado durante emit interleaved; _runs_pos() agrupa consecutivos para compre | sempre; alocados na Fase A para cada piece ('lit' ou fragmento ref herdado) |
| **Virtual refs (aliases)** | marcador | [src/tcf/composicional/syntax.py:3-5, 223-362](../../../src/tcf/composicional/syntax.py) | virtual_id = -alias_temp; alias_temp starts at 1, incrementa em _detect_compositions; alias_to_sub m | Fase B: em iterações greedy quando sub-tupla R>=2 e net>0; Fase C: emissão inlin |
| **Detector greedy (Fase B)** | filtro | [src/tcf/composicional/syntax.py:225-362](../../../src/tcf/composicional/syntax.py) | R >= 2 (mínimo 2 ocorrências); net > 0 (threshold lucro); max_iterations = 99; virtual_count <= 1 (n | Sempre na Fase B após tokenização; continua enquanto houver candidato com net>0 |
| **Net gain criterion** | threshold | [src/tcf/composicional/syntax.py:288-302](../../../src/tcf/composicional/syntax.py) | baseline > 0; n_tam = len(str(atom_count + comp_acc_k + K - 1)); lucro absoluto = (R-1) * (baseline  | Em toda iteração; cada candidato avaliado, melhor fica no 'best' |
| **Body-order constraint (inline expansion correctness)** | filtro | [src/tcf/composicional/syntax.py:267-287, 495-541](../../../src/tcf/composicional/syntax.py) | virt_pos = índice do virtual em sub (0-based); virt_alias = -sub[virt_pos]; alias_first_line[virt_al | Na detecção, quando virtual_count==1 e virt_pos>0; rejeita candidato se violado |
| **Escape mechanism (_escape_lit)** | helper | [src/tcf/composicional/syntax.py:52-73](../../../src/tcf/composicional/syntax.py) | chars escapados: {*, \, ~, 0-9}; escape_char = \; nenhuma normalização de CRLF | Em toda literal 'lit' piece durante _emit_body (linha 445) |
| **Range compression (M1.E syntax)** | heuristica | [src/tcf/composicional/syntax.py:91-101, 104-114](../../../src/tcf/composicional/syntax.py) | L >= 3 threshold pra range (linha 97, 110); consecutive check: next == prev+1; delimiter: `,` em ref | Sempre em emit, quando há >=2 consecutivos em run |
| **RLE marker: *N|linha** | marcador | [src/tcf/composicional/syntax.py:416, 462-463, 748-759](../../../src/tcf/composicional/syntax.py) | count >= 1; 'resto' = linha body ou `^eid` se repetição de ja-decodificado | Sempre em emit quando count>1 (linha 415, 462) |
| **RLE reference: ^eid** | marcador | [src/tcf/composicional/syntax.py:416-418, 754-755](../../../src/tcf/composicional/syntax.py) | eid >= 1; eid in [1..len(nos_decl)] | Quando is_rep=True em line_meta (eid ja emitido antes) |
| **Seq-RLE marker: *N+delta|template (ADR-0016)** | marcador | [src/tcf/composicional/hcc_seqrle.py:150-228, 230-274](../../../src/tcf/composicional/hcc_seqrle.py) | delta: int (uniform) OR list[int] (per-run); restrict Fase 1: máximo 1 non-zero em lista; escape-dig | Post-encode em HCCSeqRLE.encode, após super().encode; detecta em decode se `*... |
| **Comma separator (ref concat ephemeral)** | marcador | [src/tcf/composicional/syntax.py:92-102, 451, 673-681, 685](../../../src/tcf/composicional/syntax.py) | sempre between unidades ref; split character em decoder | Entre two 'refs' pieces, ou dentro run de refs atoms/compositions |
| **Tilde compositor (ref concat compositional)** | marcador | [src/tcf/composicional/syntax.py:104-114, 113, 435, 678, 685](../../../src/tcf/composicional/syntax.py) | sempre em pairwise; cada pair aloca 1 ID intermediário; K refs = K-1 IDs | Em _emit_composition quando chain de refs em alias definition |
| **Dot-dot range (syntactic sugar)** | token-type | [src/tcf/composicional/syntax.py:91-101, 104-114, 674-676, 686-688](../../../src/tcf/composicional/syntax.py) | A, B inteiros >= 1; B >= A; no spaces; apenas em grupos >=3 consecutivos | Em _runs_pos identificação de consecutivos |
| **Literal separator `*` (lit-lit ou boundary)** | marcador | [src/tcf/composicional/syntax.py:433-442, 450-453, 667-668, 720](../../../src/tcf/composicional/syntax.py) | single `*` sem sufixo | Sempre em lit-lit boundary ou ambiguous lit start |
| **Pairwise left-associativity (emit strategy)** | decision-point | [src/tcf/composicional/syntax.py:495-541, 529-538](../../../src/tcf/composicional/syntax.py) | base = current_id antes allocation; idx = position no linear chain; K = len(linear) | Em toda primeira emissão de alias (linha 507) |
| **Inline expansion (virtual resolution)** | decision-point | [src/tcf/composicional/syntax.py:495-541](../../../src/tcf/composicional/syntax.py) | recursão em expand() lexical; base ID allocation durante linear build; completions resolve in order | Em _emit_alias primeira execução, ou em _emit_ref_run quando refs[i]<0 |
| **Body-order ID assignment (interleaved atoms+compositions)** | decision-point | [src/tcf/composicional/syntax.py:391-468](../../../src/tcf/composicional/syntax.py) | current_id starts at 0 (linha 399); incrementa atomicamente por operação emit | Durante todo _emit_body |
| **Prev_lit_term_digit tracking** | decision-point | [src/tcf/composicional/syntax.py:425, 445, 452-453, 458](../../../src/tcf/composicional/syntax.py) | boolean; resetado a False exceto em 'lit' pieces | Após _escape_lit em 'lit' pieces |
| **Fragment tracking (_tokenize_pieces)** | helper | [src/tcf/composicional/syntax.py:151-221](../../../src/tcf/composicional/syntax.py) | proximo_idx starts at 1, incrementa per fragment; eid=element id (1-based); (a,b,idx) tuples stored  | Em _tokenize_pieces, uma vez pra cada string única |
| **RLE adjacency grouping (_rle_adjacente)** | helper | [src/tcf/composicional/syntax.py:42-50](../../../src/tcf/composicional/syntax.py) | ordem preservada; apenas run consecutivos agrupados | Início de _tokenize_pieces |
| **Piece structure (lit vs refs)** | categoria | [src/tcf/composicional/syntax.py:152, 204-217](../../../src/tcf/composicional/syntax.py) | pieces = [('lit'\|'refs', ...), ...]; refs list tem mixed signs | Saída de _tokenize_pieces |
| **RLE hit detection (is_rep)** | decision-point | [src/tcf/composicional/syntax.py:163-166, 407-420](../../../src/tcf/composicional/syntax.py) | eid_emitido = set de eids já vistos; is_rep boolean por line_meta | Durante _tokenize_pieces quando iterando _rle_adjacente |
| **Estimator de baseline (_estimate_baseline_chars)** | heuristica | [src/tcf/composicional/syntax.py:364-387](../../../src/tcf/composicional/syntax.py) | n_est = len(str(atom_count+comp_acc_k+1)); virtual estimate = '9'*n_est | Em _detect_compositions pra cada candidato |
| **Sub-first-line e alias-first-line tracking** | marcador | [src/tcf/composicional/syntax.py:239-264, 284-287](../../../src/tcf/composicional/syntax.py) | 0-based indices; initially empty dicts, populated em scanning | Em toda iteração detector, antes candidato filtering |

### Detalhamento

**`Atomic refs`** (marcador, [src/tcf/composicional/syntax.py:3-5, 26-28](../../../src/tcf/composicional/syntax.py))  
IDs positivos (1,2,3,...) que representam strings atômicas (literais ou tokens OBAT). Allocados sequencialmente durante tokenização da Fase A. Cada átomo recebe um prov_id (provisional) durante _tokenize_pieces, depois remapeado para final_id durante _emit_body. Coexistem no mesmo espaço de refs com referências virtuais.

**`Virtual refs (aliases)`** (marcador, [src/tcf/composicional/syntax.py:3-5, 223-362](../../../src/tcf/composicional/syntax.py))  
IDs negativos (-1,-2,...) que representam composições detectadas. Um -alias_temp refere alias_to_sub[alias_temp], lista de elems (positivos atoms ou negativos inner aliases). Emitidos como cadeias composicionais no body. Estratégia unificada: detector vê atoms + virtuals na mesma fila, permitindo pares como (atom_X, composição_anterior).

**`Detector greedy (Fase B)`** (filtro, [src/tcf/composicional/syntax.py:225-362](../../../src/tcf/composicional/syntax.py))  
Itera até convergência (max 99 iterations linha 359). A cada iteração: (1) conta sub-tuplas K>=2 em ref sequences; (2) computa net = (R-1)*(baseline_chars - num_len) onde baseline=emit length sem composição, num_len=len(str(N)) p/ ID novo; (3) filtra candidatos net>0 + constraints (virtuais em pos 0 OU alias_first_line < sub_first_line); (4) pick argmax(net); (5) substitui todas ocorrências de best.sub por alias novo. Interrompe quando best=None.

**`Net gain criterion`** (threshold, [src/tcf/composicional/syntax.py:288-302](../../../src/tcf/composicional/syntax.py))  
Heurística central do detector: net = (R-1) * (baseline - n_tam), onde R=ocorrências, baseline=chars se emitido `,`-separado inline, n_tam=len(str(próx_id)). Positivo = lucro em bytes se criar novo ref. Negativo/zero = descarta. Tie-break: Counter order (primeiro encontrado ganha). Estimativa de baseline em _estimate_baseline_chars monta ranges L>=3 e estima ~2 digits por virtual.

**`Body-order constraint (inline expansion correctness)`** (filtro, [src/tcf/composicional/syntax.py:267-287, 495-541](../../../src/tcf/composicional/syntax.py))  
Quando um sub contém virtual -Y em posição >0, filtra se alias_first_line[Y] >= sub_first_line[sub]. Sem isso, inline expansion falharia: ao emitir def de sub, Y ainda não resolvido. Com constraint garantido, pairwise left-assoc de Y já tem final_id. Decisão acontece em _detect_compositions; emissão em _emit_alias com expand() recursivo.

**`Escape mechanism (_escape_lit)`** (helper, [src/tcf/composicional/syntax.py:52-73](../../../src/tcf/composicional/syntax.py))  
Prefixo `\` (backslash) escapa chars reservados: `*` (RLE marker), `\` (escape self), `~` (compositor), dígitos (ref start). Lógica: iterator por char; se digit, coleta run contígua e prefixo com `\`; se `*`/`\`/`~`, single char escape. Retorna (text_escaped, prev_lit_term_digit) onde bool indica se último char é digit (usado pra decidir `*` separator próxima piece).

**`Range compression (M1.E syntax)`** (heuristica, [src/tcf/composicional/syntax.py:91-101, 104-114](../../../src/tcf/composicional/syntax.py))  
Runs de refs consecutivos length>=3 emitidos como `A..B` range em vez de `A~A+1~...~B`. Em _emit_refs_range: groups by _runs_pos, cada run L>=3 vira `start..end`, else individual. Joined por `,` (concat efêmero). Em _emit_composition: analoga mas joined por `~` (compositor). Decoder inverte ranges via range(int(a), int(b)+1).

**`RLE marker: *N|linha`** (marcador, [src/tcf/composicional/syntax.py:416, 462-463, 748-759](../../../src/tcf/composicional/syntax.py))  
Formato `*N|resto` onde N=count inteiro, resto=body linha. Representa N repetições idênticas de mesma string única. Encode: agrupado em _rle_adjacente (linhas consecutivas idênticas), eid emitido; se eid já visto, emite `*count|^eid`. Decode: split `*` e `|`, parse count, emite resto N vezes. Compatível com seq-RLE (ADR-0016).

**`RLE reference: ^eid`** (marcador, [src/tcf/composicional/syntax.py:416-418, 754-755](../../../src/tcf/composicional/syntax.py))  
Sintaxe `^N` onde N=eid (elemento id 1-based da lista decodificada anterior). Emitido quando linha repeats de string única ja decodificada previamente em diferente grupo RLE não-consecutivo. Decode: busca nos_decl[eid-1], append N vezes. Bug fix 2026-05-15: `^eid` + count agora emite `*count|^eid` pra preservar repetições em grupos separados (linha 415-418).

**`Seq-RLE marker: *N+delta|template (ADR-0016)`** (marcador, [src/tcf/composicional/hcc_seqrle.py:150-228, 230-274](../../../src/tcf/composicional/hcc_seqrle.py))  
Format `*N+delta|template` ou `*N+d1,d2,...|template`. Post-process em compact_body: detecta runs near-identical (mesmo length, escape-digit runs em mesmas posições, diffs apenas dentro runs). Single delta uniform: emite `*N+delta|` (M10 compat). Multi-delta (ADR-0016 Fase 1): `*N+d1,d2,d3,...|template` (CSV per-run se 1 único non-zero + zeros). Decoder expand_seq_marker: difere pelo `+` vs puro RLE `*N|`, shifta escape-digits por delta(s).

**`Comma separator (ref concat ephemeral)`** (marcador, [src/tcf/composicional/syntax.py:92-102, 451, 673-681, 685](../../../src/tcf/composicional/syntax.py))  
Delimitador `,` une refs/ranges em single line sem criar novo ref. Sintaxe: `1,2,3` (refs atom), `1..5,10,15` (ranges+atoms), `1~2,3~4` (compositions). Emit em _emit_ref_run linha 493. Decode em _parse_decl: split por `,` antes de processar cada unit (que pode ter `~` ou `..'). Múltiplas refs=múltiplas pieces emitem `,` between (linha 451). BUG FIX ADR-0007: lit começando com `,` após refs requer `*` separator pra não ser consumido como ref continuation.

**`Tilde compositor (ref concat compositional)`** (marcador, [src/tcf/composicional/syntax.py:104-114, 113, 435, 678, 685](../../../src/tcf/composicional/syntax.py))  
Delimitador `~` une refs E cria novo ref nomeado via pairwise left-assoc. Sintaxe: `1~2~3` emite seq de intermediários. Em decoder: refs [1,2,3] -> pairwise concat ID-1=(1+2), ID-2=(ID-1+3), exporta ID-2. Emit em _emit_composition (composition def) vs _emit_refs_range (atoms). BUG FIX ADR-0007: lit começando com `~` após refs requer `*` separator.

**`Dot-dot range (syntactic sugar)`** (token-type, [src/tcf/composicional/syntax.py:91-101, 104-114, 674-676, 686-688](../../../src/tcf/composicional/syntax.py))  
Syntax `A..B` shorthand para range [A, A+1, ..., B] de refs consecutivos. Encoder usa quando L>=3 consecutivos (linha 97, 110). Decoder recognizes `..` pattern (linha 675-676) e expanda via range(int(a), int(b)+1) (linha 688). Case particular de _emit_composition/refs_range.

**`Literal separator `*` (lit-lit ou boundary)`** (marcador, [src/tcf/composicional/syntax.py:433-442, 450-453, 667-668, 720](../../../src/tcf/composicional/syntax.py))  
Single `*` sem count/pipe emitido: (1) entre duas 'lit' pieces sucessivas (linha 434), (2) após refs->lit se lit começa com `,` ou `~` (ADR-0007 bug fix linha 435-442), (3) após lit com digit final->refs (linha 453). Decoder: skip quando em ref mode (linha 667-668, 720-breaking conditions). Função: desambiguação limites lit/ref pra parser single-pass.

**`Pairwise left-associativity (emit strategy)`** (decision-point, [src/tcf/composicional/syntax.py:495-541, 529-538](../../../src/tcf/composicional/syntax.py))  
Quando emitir alias definition (chain de K elementos), aloca K-1 IDs por pairwise expansion: ID_1 = elem0 + elem1, ID_2 = ID_1 + elem2, ..., ID_{K-1} = ID_{K-2} + elemK. Em _emit_alias, build linear chain via expand() recursivo, depois aloca IDs by pairwise position: alias_to_final[ali] = base + idx (idx=índice no chain linear, idx>=1). Garante correctness de inline expansion com virtual refs (constraint body-order).

**`Inline expansion (virtual resolution)`** (decision-point, [src/tcf/composicional/syntax.py:495-541](../../../src/tcf/composicional/syntax.py))  
Quando emitir virtual ref, resolve recursivamente: se já emitido (final_id em state), emit bare ID; senão, flatten sub recursivamente (expand inner aliases em order), aloca K-1 IDs pairwise, atribui finals. Completions tracking (list de (linear_idx, alias)) registra onde cada alias resolva no chain. Permite composition of compositions.

**`Body-order ID assignment (interleaved atoms+compositions)`** (decision-point, [src/tcf/composicional/syntax.py:391-468](../../../src/tcf/composicional/syntax.py))  
Single-pass emit: current_id increments sequencialmente enquanto percorre pieces (lit/refs). Atoms = +1 per piece (linha 443). Compositions = +K-1 (K=chain length, linha 532). Permite decoder single-pass sem preâmbulo: IDs assignados na ordem parse body.

**`Prev_lit_term_digit tracking`** (decision-point, [src/tcf/composicional/syntax.py:425, 445, 452-453, 458](../../../src/tcf/composicional/syntax.py))  
Booleano mantém se última literal emitida termina em digit (via _escape_lit retorno). Usado pra decidir: se prev_lit_term_digit AND próx é 'refs' -> emit `*` separator (linha 452-453) pra evitar parser confundir `abcd1,2` como `abcd` + `1,2` com count. ADR-0007 mitigation.

**`Fragment tracking (_tokenize_pieces)`** (helper, [src/tcf/composicional/syntax.py:151-221](../../../src/tcf/composicional/syntax.py))  
Fase A: quebra strings em fragments (pedaços de literal/ref). frags_por_no[eid] = lista (a,b,idx) onde [a:b] é substring e idx é fragment_id. quebras[eid] = set de boundary positions (onde refs terminam). Base em OBAT tokens: TokLit -> literal fragment; TokRefPref/TokRefSuf -> herança de fragments anteriores (com ajuste de posição). Permite reuse de fragments atomizados.

**`RLE adjacency grouping (_rle_adjacente)`** (helper, [src/tcf/composicional/syntax.py:42-50](../../../src/tcf/composicional/syntax.py))  
Pré-processa linhas: agrupa strings iguais consecutivas em (string, count). Input: [a,a,b,b,b,a] -> output: [(a,2), (b,3), (a,1)]. Usado em _tokenize_pieces pra detectar runs e decidir is_rep (já emitido antes).

**`Piece structure (lit vs refs)`** (categoria, [src/tcf/composicional/syntax.py:152, 204-217](../../../src/tcf/composicional/syntax.py))  
Fase A output: pieces_per_line[li] = list de ('lit', text, idx) ou ('refs', [ids]). 'lit': literal text + fragment_id. 'refs': sequence de refs (atoms/virtuals positivo/negativo). Consecutivos 'ref' pieces merged em um 'refs' tuple com lista unificada. Ordem preservada per line.

**`RLE hit detection (is_rep)`** (decision-point, [src/tcf/composicional/syntax.py:163-166, 407-420](../../../src/tcf/composicional/syntax.py))  
Se string única já decodificada em grupo RLE anterior (eid_emitido set), marca is_rep=True. Emit usa ^eid reference em vez de recompilar. Preserva bytes quando repetição em grupos não-consecutivos (bug fix 2026-05-15).

**`Estimator de baseline (_estimate_baseline_chars)`** (heuristica, [src/tcf/composicional/syntax.py:364-387](../../../src/tcf/composicional/syntax.py))  
Estima chars de emit `,`-separado de sub (misto atom/virtual) SEM criar nova composition. Para atoms: emit ranges se L>=3. Para virtuals: assume ~2 digits (estimador pessimista). Retorna len(','.join(parts)). Usado no net computation (baseline parameter).

**`Sub-first-line e alias-first-line tracking`** (marcador, [src/tcf/composicional/syntax.py:239-264, 284-287](../../../src/tcf/composicional/syntax.py))  
sub_first_line[sub] = first line index onde sub aparece como candidato. alias_first_line[alias] = first line onde alias (negativo id) aparece em body. Usado em body-order constraint: se sub tem virtual em pos>0, require alias_first_line[virt] < sub_first_line[sub].

### Notas

**CATALOGAÇÃO EXAUSTIVA — HCC M8.A CAMADA 2**

**Status Canonical & Welding**:
- Código base intocado desde 2026-05-16 em dirty lab
- Welded src/tcf 2026-05-17, Bug fixes: ADR-0006, ADR-0007, ADR-0015, ADR-0016
- Format frozen v1.0 via ADR-0017: #TCF.6 imutável até v2.0; D1-D9=1523B, D17a=322B

**Caracteres Especiais Completo**:
`*` (RLE/separator), `\\` (escape), `~` (compositor), `,` (concat-ephemeral), `..` (range), `^` (ref-anterior), `+` (seq-RLE delta), `|` (delimiter), `0-9` (IDs). Nenhum outro especial.

**Refs Atômicos vs Virtuais**:
- **Unificação M8.A**: espaço único [atoms(+), virtuals(-)] permite detector capturar pares (atom_prev, composition_last) que M7.A perderia
- **Pairwise left-assoc**: ID_i = ID_{i-1} + elem_i garante correctness inline expansion via body-order constraint

**Detector Greedy**:
- Iterativo até convergência (max 99), net = (R-1)*(baseline - n_tam), tie-break Counter order
- R>=2 obrigatório, virtual_count<=1, body-order check se virtual em pos>0
- Greedy: não tree-based, não online, pick argmax(net) cada iteração

**Escape Mechanism**:
- `\\` prefixo para digit-runs + chars {*, \\, ~}
- Tracking prev_lit_term_digit decide `*` separator (ADR-0007 mitigation, não escape `,`)
- Decoder _parse_decl reconhecer `\\` + ranges

**Seq-RLE (ADR-0016)**:
- Post-process: detect near-identical, `*N+delta|` (M10 compat) ou `*N+d1,d2,...|` (Fase 1 multi-delta)
- Restrict: máximo 1 non-zero per-run em multi-delta
- Decoder: disambigua `+` pattern, shifta escape-digits

**Fluxo Camadas Funis**:
- CAMADA 0: natures pre-tx opt-in
- CAMADA 1: OBAT tokenização
- CAMADA 2: HCC greedy + Seq-RLE post-process
- CAMADA 3: Multi-col wrapper

Owner context: estudar EXAUSTIVAMENTE TODAS estratégias ANTES explorar v2.0 (dict, lossy, sort, Patricia). Catalogo COMPLETO current.

---
