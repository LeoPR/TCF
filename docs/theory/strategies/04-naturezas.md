---
title: CAMADA 0-pre (Naturezas — Pre-transform opt-in per VALOR)
type: reference
parent: strategies-map
subsystem: naturezas
---

# CAMADA 0-pre (Naturezas — Pre-transform opt-in per VALOR)

**Como decide caminhos**:

1. **Encoder pipeline com nature** (encode com nature param):
   - Caller: encode(values, nature=SPEC_X) [list] ou encode(dict, nature_per_col={name: SPEC_X}) [dict]
   - Dispatcher (encoder.py:96-114): detecta tipo, aplica encode_value(spec, v) em cada valor → lista pré-transformada
   - Result: valores comprimidos ('5 chars base94' ou '12 dígitos padded') ou fallback ('_' + original)
   - Flow: pre-tx CAMADA 0 → analyze_column → detect_cadence → detect_min_len → OBAT → HCC
   
2. **Decoder pipeline com nature** (decode com nature param):
   - Caller: decode(text, nature=SPEC_X) [single] ou decode(text, nature_per_col={name: SPEC_X}) [multi]
   - Dispatcher (decoder.py:52-91): detecta shebang, decodifica HCC → list[str], aplica decode_value(spec, v) em cada
   - Flow: HCC decode → reverse pre-tx CAMADA 0 (strip marker ou regenerar formato original)
   
3. **classify_value flow** (diagnostic path):
   - Caller: classify_value(spec, v) [explicit] ou chamado internamente por encode_value
   - Decision points: TemplatedCheckedSpec (lines 66-81) ou TemplatedPaddedSpec (lines 63-84)
   - Result: enum string ('compressible', 'check_invalid', 'format_mismatch', 'format_unmasked', 'empty_value', 'length_wrong', 'range_invalid', 'format_padded_zeros')
   - Usado: (a) no encode_value para determinar path (compressible vs fallback), (b) explicitamente pra diagnostico via API publica
   
4. **Pre-pass heuristics flow** (sem nature — análise estrutural):
   - Entrada: values list[str]
   - analyze_column(values) → ColumnFeatures (O(N), barato)
   - detect_cadence_from_features(features, unicas) → (bool, dict info) — determina se usa OBAT shape-preserve
   - detect_min_len_from_features(features) → int {3,4,5,6} — determina granularidade tokenização
   - Output: usados em OBAT layer (CAMADA 1), HCC layer (CAMADA 2)
   - Nota: **pre-pass é orthogonal a nature** — roda depois pre-tx CAMADA 0 (em _encode_column)
   
5. **Round-trip guarantee**:
   - Com nature: encode(values, nature=SPEC_X) → text; decode(text, nature=SPEC_X) == values ✓
   - Sem nature: encode(values) → text; decode(text) == values ✓
   - Fallback marker '_' preserva valores inválidos → round-trip sempre funciona

### Estrategias (19)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **TemplatedCheckedSpec (classificação + encode/decode parametrico)** | estrategia | [src/tcf/natures/templated_checked.py:42-109](../../../src/tcf/natures/templated_checked.py) | TemplatedCheckedSpec @dataclass fields: name (str), regex (re.Pattern), body_length (int), check_len | sempre — integrado no pipeline TCF quando nature param fornecido em encode(data, |
| **classify_value — Taxonomia Kim 2003 (5 categorias + 1 fallback genérico)** | decision-point | [src/tcf/natures/templated_checked.py:64-81](../../../src/tcf/natures/templated_checked.py) | v: str (valor); expected_total = body_length + check_length; extrai digits via ''.join(c for c in v  | sempre — em cada encode_value() ou quando chamado explicitamente via classify_va |
| **BASE94 alfabeto (80 chars, safe TCF)** | token-type | [src/tcf/natures/templated_checked.py:32-36](../../../src/tcf/natures/templated_checked.py) | nenhum — constante builtin ao modulo | em encode_value() quando classify_value retorna 'compressible' (lines 90-95) |
| **MARKER_LITERAL '_' — Fallback literal prefix** | marcador | [src/tcf/natures/templated_checked.py:38](../../../src/tcf/natures/templated_checked.py) | nenhum — constante '_' | em encode_value() quando classify_value != 'compressible' (line 87); em decode_v |
| **encode_value — Base-94 encoding compressible** | estrategia | [src/tcf/natures/templated_checked.py:83-95](../../../src/tcf/natures/templated_checked.py) | v: str; status = classify_value(v) determina path; body_int = int(digits[:body_length]); n = body_in | sempre em encode() pipeline quando nature param passado (encoder.py line 98-99) |
| **decode_value — Base-94 decoding + reformatting** | estrategia | [src/tcf/natures/templated_checked.py:97-109](../../../src/tcf/natures/templated_checked.py) | payload: str; expected encoded_length e all(c in BASE94); uses check_fn(body) + formatter(body+check | em decode() pipeline quando nature param passado (decoder.py line 89-90) |
| **SPEC_CPF — (NNN.NNN.NNN-DD, mod-11 dupla)** | categoria | [src/tcf/natures/templated_checked.py:130-162](../../../src/tcf/natures/templated_checked.py) | name='cpf', regex=_CPF_RE, body_length=9, check_length=2, check_fn=_cpf_check_fn, formatter=_cpf_for | ao chamar encode(values, nature=SPEC_CPF) ou decode(text, nature=SPEC_CPF); ou e |
| **SPEC_CNPJ — (NN.NNN.NNN/NNNN-DD, mod-11 dupla pesos diferentes)** | categoria | [src/tcf/natures/templated_checked.py:165-199](../../../src/tcf/natures/templated_checked.py) | name='cnpj', regex=_CNPJ_RE, body_length=12, check_length=2, check_fn=_cnpj_check_fn, formatter=_cnp | ao chamar encode(values, nature=SPEC_CNPJ) ou decode(text, nature=SPEC_CNPJ) |
| **TemplatedPaddedSpec (TCU-NoCheckVarLength — slots padronizados sem check)** | estrategia | [src/tcf/natures/templated_padded.py:37-113](../../../src/tcf/natures/templated_padded.py) | name (str), regex (re.Pattern com grupos=slots), slot_widths (tuple int), separator (str). total_pad | sempre — Protocolo NatureSpec idêntico a TemplatedCheckedSpec (sem isinstance ch |
| **SPEC_IP — IPv4 (slot_widths=(3,3,3,3), separator='.')** | categoria | [src/tcf/natures/templated_padded.py:116-125](../../../src/tcf/natures/templated_padded.py) | name='ip', regex=_IPV4_RE, slot_widths=(3,3,3,3), separator='.' | ao chamar encode(values, nature=SPEC_IP) ou decode(text, nature=SPEC_IP) |
| **classify_value TemplatedPaddedSpec — Taxonomy (6 categorias)** | decision-point | [src/tcf/natures/templated_padded.py:63-84](../../../src/tcf/natures/templated_padded.py) | v: str; extrai slots via regex.groups(); para cada slot: int(slot_str) >= 10^width -> range_invalid; | sempre em encode_value() quando nature=SPEC_IP fornecido |
| **encode_value TemplatedPaddedSpec — Padding + preservação dígitos** | estrategia | [src/tcf/natures/templated_padded.py:86-97](../../../src/tcf/natures/templated_padded.py) | v: str; status = classify_value(v); if compressible: return ''.join(slot_str.zfill(width) for slot_s | em encode() pipeline quando nature=SPEC_IP passado |
| **decode_value TemplatedPaddedSpec — Unpadding + reformatting** | estrategia | [src/tcf/natures/templated_padded.py:99-113](../../../src/tcf/natures/templated_padded.py) | payload: str; len(payload)==total_padded_length e payload.isdigit(); cursor tracking per slot_widths | em decode() pipeline quando nature=SPEC_IP passado |
| **Integration: encode() pipeline com nature param** | estrategia | [src/tcf/encoder.py:53-114](../../../src/tcf/encoder.py) | nature: TemplatedCheckedSpec \| None, nature_per_col: dict[str, TemplatedCheckedSpec] \| None | sempre em encode() quando nature ou nature_per_col param passado; sem param = sk |
| **Integration: decode() pipeline com nature param** | estrategia | [src/tcf/decoder.py:52-91](../../../src/tcf/decoder.py) | nature: TemplatedCheckedSpec \| None, nature_per_col: dict[str, TemplatedCheckedSpec] \| None | sempre em decode() quando nature ou nature_per_col param passado; sem param = sk |
| **analyze_column — ColumnFeatures pre-pass (O(N))** | heuristica | [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py) | values: list[str], sample_size=20 (default). n_rows = len(values); n_unicas = len(set(values)); avg_ | sempre em _encode_column() (encoder.py:139), antes de detect_cadence/detect_min_ |
| **detect_cadence_from_features — Regra 1 + Regra 2** | heuristica | [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py) | features: ColumnFeatures, strings_unicas: list[str], n_sample=5 (primeiras N pra análise), threshold | em _encode_column() linha 141 (encoder.py), após analyze_column() |
| **detect_min_len_from_features — Decision tree shallow (heurística v3)** | heuristica | [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py) | features: ColumnFeatures, n_threshold=100 (gating). avg_len = features.avg_len; card = features.card | em _encode_column() linha 142 (encoder.py), após detect_cadence() output recebid |
| **Protocol NatureSpec — Polimorfismo sem isinstance** | helper | [src/tcf/natures/ (init define protocol implícito)](../../../src/tcf/natures/ (init define protocol implícito)) | nenhum — define contrato de interface, não implementação concreta | sempre — em toda integração com nature param |

### Detalhamento

**`TemplatedCheckedSpec (classificação + encode/decode parametrico)`** (estrategia, [src/tcf/natures/templated_checked.py:42-109](../../../src/tcf/natures/templated_checked.py))  
Classificador + encoder/decoder polimórfico genérico para identificadores com layout fixo (regex template), dígito verificador derivável (check_fn), e espaço único-discreto (sem ordem). Filosofia opt-in per-value: cada valor decide se comprime (base-94 encoded, 5-7 chars) ou cai em fallback literal (marcador '_' prefixado). Parametrizado por: name, regex, body_length, check_length, check_fn, formatter, encoded_length. **Protocolo**: encode_value(v)->tuple(payload,status), decode_value(payload)->str, classify_value(v)->str (taxonomy Kim 2003). Zero isinstance check — polimorfismo via spec param (Strategy pattern).

**`classify_value — Taxonomia Kim 2003 (5 categorias + 1 fallback genérico)`** (decision-point, [src/tcf/natures/templated_checked.py:64-81](../../../src/tcf/natures/templated_checked.py))  
Decision tree com 6 outcomes: (1) empty_value (v==''), (2) format_unmasked (exato body_length+check_length dígitos, isdigit()=true, mas sem máscara regex), (3) format_mismatch (regex.match falha, len<5 -> length_wrong, len>=5 -> format_mismatch), (4) length_wrong (extraído digits_str != body+check), (5) check_invalid (check digit mismatch), (6) compressible (tudo passou). Lógica exata: lines 66-81. Precedência: empty > format > length > check > compressible.

**`BASE94 alfabeto (80 chars, safe TCF)`** (token-type, [src/tcf/natures/templated_checked.py:32-36](../../../src/tcf/natures/templated_checked.py))  
Alfabeto construído dinamicamente: todos chr(33-127) EXCETO reserved set ('\n\r\t ,~*\\#=[]<>"''\'`_'). Total = 94-14(reserved)-1(marker '_') = 79 chars efetivos (verificado assert>=50, real=80). Usado em base-94 encoding compressible: n % 80, n // 80, ... Alfabeto preserva RT — charset é deterministico e cyclic (0->BASE94[0], 1->BASE94[1], etc).

**`MARKER_LITERAL '_' — Fallback literal prefix`** (marcador, [src/tcf/natures/templated_checked.py:38](../../../src/tcf/natures/templated_checked.py))  
Prefixo '_' distingue valor comprimido (base-94 encoded, 5-7 chars) de literal fallback. Ao decodificar: se payload.startswith('_'), remove marker e retorna original (line 100). Ao codificar: fallback retorna '_' + v (line 87). Semantica: '_' é um escape — tudo após é literal UTF-8 do original, preservando RT mesmo em valores não-compressible. Char escolhido porque já é reservado TCF (não em BASE94, não em regex templates típicos).

**`encode_value — Base-94 encoding compressible`** (estrategia, [src/tcf/natures/templated_checked.py:83-95](../../../src/tcf/natures/templated_checked.py))  
Two-path: (1) compressible: extrai body_int (primeiros body_length dígitos), converte pra base-94 em encoded_length chars via n%80, n//80 loop (lines 90-94), reversa ordem (chars built em little-endian, reversed ao final). (2) fallback: retorna '_' + v + status. Exemplo CPF: '529.982.247-25' -> body=529982247 -> 5 chars base94. Garante RT: se decoding recebe encoded, pode reverter sem ambiguidade.

**`decode_value — Base-94 decoding + reformatting`** (estrategia, [src/tcf/natures/templated_checked.py:97-109](../../../src/tcf/natures/templated_checked.py))  
Two-path: (1) payload começa '_': strip marker, return original (line 100). (2) payload == encoded_length chars, all chars in BASE94: convert back via base-94 positional (lines 102-108). Rebuild body_str via zfill(body_length), aplica check_fn pra recalcular checks, aplica formatter pra restaurar máscara. Exemplo: '\29g/h-' -> n=0; for c in '29g/h-': n = n*80 + BASE94.index(c); body_str = str(n).zfill(9); checks = check_fn([int(d) for d in body_str]); formatter(body + checks) -> '529.982.247-25'.

**`SPEC_CPF — (NNN.NNN.NNN-DD, mod-11 dupla)`** (categoria, [src/tcf/natures/templated_checked.py:130-162](../../../src/tcf/natures/templated_checked.py))  
Spec concreto pra CPF brasileiro. Regex=r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$', body_length=9, check_length=2, encoded_length=5 (80^5 > 10^9). Check digits via _cpf_check_fn: Mod-11 dupla — d1=(S1*10)%11 (se==10 então 0), S1=sum(d*w for d,w in zip(body, range(10,1,-1))); similar d2 com body+d1 e range(11,1,-1). Formatter recombina com máscara. RT 100% em datasets validados; comprime CPF uniform/clustered 55-64% vs M10 puro (sub-exp 05-07).

**`SPEC_CNPJ — (NN.NNN.NNN/NNNN-DD, mod-11 dupla pesos diferentes)`** (categoria, [src/tcf/natures/templated_checked.py:165-199](../../../src/tcf/natures/templated_checked.py))  
Spec concreto pra CNPJ brasileiro. Regex=r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$', body_length=12, check_length=2, encoded_length=7 (80^7 > 10^12). Check digits via _cnpj_check_fn: mod-11 com pesos _W1_CNPJ=[5,4,3,2,9,8,7,6,5,4,3,2] e _W2_CNPJ=[6,5,4,3,2,9,8,7,6,5,4,3,2], diferente de CPF. Lógica: d1=0 se rem1<2 else 11-rem1. Formatter restaura máscara. RT 100%; comprime 54-61% vs M10 puro em datasets validados.

**`TemplatedPaddedSpec (TCU-NoCheckVarLength — slots padronizados sem check)`** (estrategia, [src/tcf/natures/templated_padded.py:37-113](../../../src/tcf/natures/templated_padded.py))  
Variante de TemplatedCheckedSpec para dados SEM dígito verificador (ex: IPv4). Slots de width variável são padronizados via padding zero-leading. Diferenças: (1) sem check_fn, (2) sem base-94 (preserva dígitos pra HCC seq-RLE detectar cadência), (3) slot_widths tuple fixo. Exemplo: '192.168.1.1' -> slots=['192','168','1','1'] + slot_widths=(3,3,3,3) -> padded='192168001001' (12 dígitos). classify_value retorna 'format_padded_zeros' se slot str(int(slot))!=slot (detecta padding não-canonical, ex: '192.168.01.1'). RT 100%; D-IP-subnet comprime 1.71% ratio vs M10 puro (speedup 68x, sub-exp 08).

**`SPEC_IP — IPv4 (slot_widths=(3,3,3,3), separator='.')`** (categoria, [src/tcf/natures/templated_padded.py:116-125](../../../src/tcf/natures/templated_padded.py))  
Spec concreto pra IPv4 canonical (sem zeros líderes em octetos, ex: '192.168.1.1'). Regex=r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'. encode_value: zfill cada slot a 3 dígitos, concatena -> '192168001001'. decode_value: split em 4 chunks de 3 dígitos, remove leading zeros via str(int(slot)), rejoin com '.'. Ganho em D-IP-subnet (1000 IPs /24) = 229B (1.71% ratio) vs M10 puro 13349B — HCC seq-RLE detecta cadência quando IPs em subnet; em D-IP-uniform (aleatório) = 102% (pior sem estrutura, esperado).

**`classify_value TemplatedPaddedSpec — Taxonomy (6 categorias)`** (decision-point, [src/tcf/natures/templated_padded.py:63-84](../../../src/tcf/natures/templated_padded.py))  
Decision tree: (1) empty_value (v==''), (2) format_mismatch (regex.match falha), (3) range_invalid (slot int >= 10^width, overflow), (4) format_padded_zeros (str(int(slot))!=slot original — ex: '192.168.01.001' tem padding não-canonical), (5) compressible (todas slots parseáveis como int, no overflow, sem padding). Precedência idêntica a TemplatedCheckedSpec. Linha 82-83: detecta padding não-canonical via `str(val) != slot_str`.

**`encode_value TemplatedPaddedSpec — Padding + preservação dígitos`** (estrategia, [src/tcf/natures/templated_padded.py:86-97](../../../src/tcf/natures/templated_padded.py))  
Dois paths: (1) compressible: extrai slots via regex.groups(), zfill cada slot a width, concatena em padded string digit-only (ex: '192.168.1.1' -> '192168001001'). (2) fallback: return '_' + v. Diferença vs TemplatedCheckedSpec: sem base-94 — preserve dígitos visíveis pra HCC seq-RLE digit-centric detectar cadência. Fallback marker idêntico ('_' prefix).

**`decode_value TemplatedPaddedSpec — Unpadding + reformatting`** (estrategia, [src/tcf/natures/templated_padded.py:99-113](../../../src/tcf/natures/templated_padded.py))  
Dois paths: (1) payload começa '_': strip, return original. (2) payload == total_padded_length, all chars digit: split em slot_widths chunks, convert cada via str(int(slot)) pra remover leading zeros, rejoin com separator. Exemplo: '192168001001' -> chunks=['192','168','001','001'] -> [str(int(...))] = ['192','168','1','1'] -> '.'.join() = '192.168.1.1'. RT 100%.

**`Integration: encode() pipeline com nature param`** (estrategia, [src/tcf/encoder.py:53-114](../../../src/tcf/encoder.py))  
Dispatcher: (1) list[str] + nature param: applica encode_value(nature, v) em CADA valor antes do M10 pipeline (lines 97-99), resultando em list[str] com valores já pré-transformados (comprimidos ou fallback). (2) dict + nature_per_col param: para cada coluna name, if name in nature_per_col, aplica encode_value(nature_per_col[name], v) em todos valores da coluna (lines 104-109). Filosofia: nature é **CAMADA 0 do funil** — anterior a analyze_column/detect_cadence/OBAT/HCC. Sem nature param: comportamento M10 inalterado (byte-canonical preservado, D17a 322B INVARIANT).

**`Integration: decode() pipeline com nature param`** (estrategia, [src/tcf/decoder.py:52-91](../../../src/tcf/decoder.py))  
Dispatcher: (1) single-col: decode_column retorna list[str] (HCC decoded), aplica decode_value(nature, v) em cada v (lines 88-90). (2) multi-col: _decode_multi retorna dict (HCC decoded), aplica decode_value(nature_per_col[name], v) em cada coluna (lines 79-85). Filosofia: decoder é **espelho de encoder** — mesma nature spec obrigatória out-of-band (decoder não auto-detecta; futuro v2 carry spec em header). Sem nature param: skip reverse (valores já em formato original via '_' marker fallback ou HCC canonical).

**`analyze_column — ColumnFeatures pre-pass (O(N))`** (heuristica, [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py))  
Pre-pass unificado: calcula features básicas em 1 passada O(N) — n_rows, n_unicas (via set(values)), avg_len, cardinality=n_unicas/n_rows, is_numeric (sample check float parse), sample (primeiros 20 strings). Recebido por downstream heuristicas (detect_cadence, detect_min_len, futuras detect_X naturezas). Reduz duplicação + permite reuso. Welded T-CODE-H-DA-11c (2026-05-22). Nota: **sem natureza** — apenas features, não aplica pré-tx.

**`detect_cadence_from_features — Regra 1 + Regra 2`** (heuristica, [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py))  
Detecta estrutura cadencial (wrapper+counter ou numeric high-card) pra ativar OBAT shape-preserve hint. **Regra 1** (uniform-length + high-LCP-LCS): primeiras N strings length uniforme, calcula LCP+LCS entre pares consecutivos, ratio=(LCP+LCS)/length; se TODOS ratios >= threshold (default 0.7), aciona. **Regra 2** (numeric high-cardinality, ADR-0008): features.is_numeric=true E cardinality > 0.5, aciona. Retorna (detectou:bool, info:dict com detalhes). Se detecta: encoder chama processar_with_hint(prefer_shape_consistency=True) em vez de processar() canonical (obat_shape.py).

**`detect_min_len_from_features — Decision tree shallow (heurística v3)`** (heuristica, [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py))  
Decision tree pra min_len ótimo (enum {3,4,5,6}), captura 99.5% oracle real-world. Gating: n_rows < 100 -> 3 (preserva M9 baseline 1615B exato). Senão: card<0.2 -> 3; avg>=25 -> 6; avg>=8 && card>=0.4 -> 6; avg>=5 && is_numeric && card>=0.8 -> 6; avg>=12 && card>=0.7 -> 5; avg>=3 && card>=0.2 -> 4; else -> 3. Exemplos: D-CPF (baixa card) -> 3; D-datas-mundiais (avg=10, card=0.8) -> 6; D-ID-seq (avg=5, is_num=true, card=0.95) -> 6.

**`Protocol NatureSpec — Polimorfismo sem isinstance`** (helper, [src/tcf/natures/ (init define protocol implícito)](../../../src/tcf/natures/ (init define protocol implícito)))  
Estratégia de design: toda spec (TemplatedCheckedSpec, TemplatedPaddedSpec, futuras) implementa o mesmo Protocol: name:str, encode_value(v)->tuple(str,str), decode_value(payload)->str, classify_value(v)->str. Encoder/decoder são polimorfo (genéricos) — **zero isinstance(spec, TemplatedCheckedSpec)** em qualquer lugar (confirmado linha 20 encoder.py comentário). Permite adicionar specs novas (Luhn, IBAN, MAC, CEP) sem mudar API publica nem core pipeline. Refactoring 2026-05-24: converteu encode_value/decode_value/classify_value de standalone functions (backward compat mantido) para **methods no spec** (@dataclass frozen, immutable).

### Notas


**CAMADA 0-pre Natures subsystem — Resumo técnico exhaustivo:**

1. **Filosofia opt-in per-value**: cada valor **decide individualmente** se comprime. Sem "all-or-nothing" — fallback literal ('_' marker) preserva RT sempre. Compressão ocorre quando valor passa validate (regex + check digit). Não-compressible caem em fallback automaticamente.

2. **Dois tipos de specs atuais**:
   - **TemplatedCheckedSpec** (CPF, CNPJ): layout fixo + dígito verificador derivável → base-94 encoded (5-7 chars)
   - **TemplatedPaddedSpec** (IP): layout fixo, slots padronizados via padding, **sem check** → digit-only padded (preserva visibilidade HCC seq-RLE)

3. **Polimorfismo Protocol-based**: encoder/decoder são **genéricos** — não há isinstance() check. Permite adicionar specs futuras (Luhn, IBAN, MAC, CEP) sem mudar pipeline core. Strategy pattern puro.

4. **Integração CAMADA 0-do funil**:
   - Pre-tx CAMADA 0 (nature): `encode_value(spec, v)` per-valor, **antes** de analyze_column
   - CAMADA 1 (pre-pass): detect_cadence, detect_min_len sobre ColumnFeatures (sem nature interference)
   - CAMADA 2 (OBAT): tokenization com hints
   - CAMADA 3 (HCC): composicional + seq-RLE

5. **Byte-canonical INVARIANT preservado**: sem nature param = sem mudança. D17a 322B INVARIANT validado. Default M10 comportamento é seguro — backwards compatible 100%.

6. **Fallback marker '_'**: escape character. Todos valores inválidos, empty, ou não-matching regex caem aqui. Decoder reconhece '_' prefix → strip → retorna original. Garante round-trip lossless **sempre**.

7. **Check digit semântica**:
   - **CPF**: Mod-11 dupla com pesos range(10,1,-1) e range(11,1,-1); se resto==10 então check=0
   - **CNPJ**: Mod-11 com pesos específicos _W1, _W2; se rem<2 então 0, else 11-rem
   - **IP**: sem check — apenas padding

8. **Validação real-world (sub-exps 05-08)**:
   - CPF 50 vals: 942B (M10) → 337B (nature) = **-64%**
   - CNPJ 50 vals: similar **-54 a -61%**
   - D-IP-subnet 1000: **1.71% ratio** (vs M10 13349B) — **speedup 68x**
   - D-IP-uniform 200: 102% (pior, sem cadência — esperado)
   - RT 100% todos datasets; tests 192 passed

9. **Decode reversibility**: decoder requer **same spec out-of-band**. Futuro v2 carry spec em header. Atualmente: caller responsável prov spec.

10. **Threshold/Heuristic landscape**:
    - `MARKER_LITERAL = '_'` — fixo, não tunável (parte do formato TCF)
    - `BASE94 = 80 chars` — fixo (segurança charset TCF)
    - `encoded_length` por spec — fixo (derivado body_length via capacity math)
    - `detect_cadence threshold = 0.7` — tunável futuro (T-CODE-LAYERED-PIPELINE Fase 2)
    - `detect_cadence numeric_card_threshold = 0.5` — tunável futuro
    - `detect_min_len n_threshold = 100` — tunável futuro (gating)

11. **Gaps/TODO v2.0 (ADR-0018 roadmap)**:
    - Auto-detect natures via apply_rate threshold (Schema_builder Fase 3)
    - Header carry spec id (decoder auto-detecta)
    - Lossy-recoverable (H-LR-*) — quando dataset real disponível
    - Strip-sufixo (V2-D) — composite Templated+Enumerated
    - IBAN, Luhn, MAC, CEP specs — quando datasets reais validarem necessidade
    - Fallback adaptativo (partial compress, hybrid)

12. **Code reachability**:
    - encode() entry: encoder.py:53-114 (lines 97-109 nature dispatch)
    - decode() entry: decoder.py:52-91 (lines 79-90 nature dispatch)
    - ColumnFeatures pre-pass: column_features.py:51-84
    - Cadence heuristic: auto_cadence.py:28-96 (2 regras, lines 64-93)
    - Min_len heuristic: auto_min_len.py:25-68 (decision tree, lines 49-68)
    - Specs registry: natures/__init__.py:34-63 (exports SPEC_CPF, SPEC_CNPJ, SPEC_IP)

13. **Documentação canonical**:
    - ADR-0015: decision + welding rationale
    - use-natures.md: how-to + exemplos
    - data-natures-taxonomy.md: teoria 8 naturezas
    - tests/test_natures.py + test_natures_ip.py: validação


---
