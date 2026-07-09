# Bases / radix em cada parte do TCF — mapa pra fechar aos poucos [reference→proposta]

**Data**: 2026-07-09. **Owner**: "revisar os usos de formatos de base em cada parte do TCF; focar por
enquanto no ganho imediato (hex-default no header); usar bases diferentes em outras áreas a gente vai
estudando e fechando aos poucos." Este é o **registro** — cada sítio onde um NÚMERO entra no formato, qual
base usa, e o status. Fonte: survey `tcf-radix-survey` (5 leitores + crítico de completude, file:line
verificados). Ticket do ganho imediato: [T-FMT-HEADER-BASE-HEX](../../../../tickets/T-FMT-HEADER-BASE-HEX.md).

> **Regra de ouro achada pelo survey**: hex-default só faz sentido onde o número é **delimitado por
> separador e NÃO encosta em texto literal**. No corpo (refs `^N`, ref-stream, seq-RLE) o número usa o
> **digit-escape `\<digits>`** — pôr hex ali estende o alfabeto numérico pra `a-f` e **colide com o literal**
> (um `a-f` de texto viraria dígito). Por isso o header é o lugar CERTO e o corpo é o lugar ERRADO.

## Os 4 baldes

### A. FECHAR AGORA — header byte-sizes → HEX-default (ganho imediato)
| sítio | onde | base hoje | ação |
|---|---|---|---|
| size `NN=nome` (emit) | `multi/core.py:234` | decimal (`f"{len(b)}=…"`) | → hex (`{len(b):x}`) |
| size anônimo bare (emit) | `multi/core.py:230` | decimal | → hex |
| size parse (decode) | `multi/core.py:349,357` | `int(size_str)` | → `int(_,16)` lockstep |
| **size re-parse (lazy)** | **`view.py:99,104`** | `int(size_str)` | → `int(_,16)` **lockstep (o survey pegou; naive-switch quebraria o lazy)** |
| n_est / prune width | `composicional/syntax.py:328-329,354` | `len(str(id))` | **não é size do header** — não muda (refs ficam decimais) |

- **Round-trip / colisão**: `{:x}` = minúsculo, sem zero à esquerda, canônico; `int(_,16)` reverte. Alfabeto
  `[0-9a-f]` disjunto de `, = : { } [ ] \n` e dos prefixos `! @ %`; size é `=`-delimitado (ou bare posicional)
  → sem ambiguidade. Byte-monotônico não-crescente (economiza 1 char p/ len em [16,255],[4096,65535],…; empata
  no resto; **nunca pior**). Só K−1 sizes/tabela (última é sem-size, O-FMT-15) → economia em ≤ K−1 colunas.
- **Pin que move**: **D17a** (303B, multi-col, re-pinável ADR-0024/0025). **Real-world NÃO move** (snapshots
  são single-col, sem meta de size). Weld gated (go src/tcf + re-pin + suite verde).

### B. JÁ ÓTIMOS — não mexer (hex seria PIOR)
| sítio | onde | base | por quê |
|---|---|---|---|
| índice `@dict` V2-B (stream) | `multi/dict_v2b.py:16-43,80-84` + `view.py:35-40` (2º decoder) | base-94 (0x21–0x7E, exclui `\n`) | 1 símbolo/byte, byte-length-delimitado (não usa separador) → hex dobraria o stream |
| largura `@dict` `_v2b_width` | `dict_v2b.py:26-32` | base-94 | K≤8192<94² → width≤2 |
| bN índices (research) | labs `bn_codec.py`/`bn_f3.py` | bits (w∈{1,2,4}) | binário sub-byte, mais denso que qualquer textual |
| nature CPF/CNPJ payload | `natures/templated_checked.py:89-95` | **base-80** (alfabeto "BASE94" é misnomer, len=80) | hex EXPANDE (16<80); payload size-delimitado |

### C. LOCKED decimal — hex QUEBRARIA (não mexer nunca, ou com muito cuidado)
| sítio | onde | por que travado |
|---|---|---|
| `^N` line-ref | `syntax.py:477,479,541` | encosta em literal; digit-escape `\<digits>` → hex colide com `a-f` literal |
| ref-stream atom ids + `A..B` | `syntax.py:131-136,588` | maior população de ids, mas mesmo escape-boundary; detector de run/range é base-aware |
| seq-RLE deltas `*N+d\|tmpl` | `hcc_seqrle.py:91-95,191,229-255` | **aritmética** sobre dígitos-fonte byte-canônicos; re-basear quebra round-trip + template |
| IP nature payload | `natures/templated_padded.py:93-97` | digit-preserving (192168001001); design depende da visibilidade decimal |
| ref-expr decoder (`isdigit`) | `syntax.py:663-699` | alfabeto `isdigit()`=0-9; alargar p/ hex confunde `a-f` literal com dígito |

### D. GRADUAL / maybe — marginal, estudar depois (cada um no seu tempo)
| sítio | onde | base | nota |
|---|---|---|---|
| `<ntable>\n` prefixo V2-B | `dict_v2b.py:66,74` + `view.py:170` | decimal, `\n`-terminado | hex colisão-livre, mas salva ~1 char só em tabela multi-KB |
| split `%` `<ntmpl>` + per-part | `multi/split.py:55` | decimal, `\n`/`:`-delim | hex colisão-livre com `\n`/`:`; ganho pequeno; tocaria ADR-0026 |
| RLE/seq-RLE counts `*N\|` | `syntax.py:477,541`; `hcc_seqrle.py:191` | decimal | counts minúsculos (<16) → ~0 byte, custa inspecionabilidade |

### Fora de radix (nem é número/base)
- `#TCF.N` minor (`core.py:59-68`): dígito semântico único, base irrelevante.
- nature-id `:cpf` (`core.py:225`): token alfabético, vocab fechado.
- `min_len`/`cadence`: nunca entram no blob (encode-param + SideOutputs).
- `drop_names`: índice nunca serializado (só a posição da vírgula).

## Ordem de fechamento (proposta)
1. **A** (header hex) — agora, ticket próprio ([T-FMT-HEADER-BASE-HEX](../../../../tickets/T-FMT-HEADER-BASE-HEX.md)), weld gated.
2. **D** (ntable, split, counts) — quando o nicho payload-minúsculo pagar; cada um mede o próprio ganho.
3. **B/C** ficam como estão (documentar que são fechados por design, não candidatos).

## Cross-links
- Ticket imediato: [T-FMT-HEADER-BASE-HEX](../../../../tickets/T-FMT-HEADER-BASE-HEX.md) ·
  desmembrado de [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) Item 1.
- Primitiva de índice (radix é 1 dos 4 eixos): [dict-referencia-hipoteses](dict-referencia-hipoteses.md) +
  [vocabulary §Primitiva](../../../../docs/vocabulary.md).
- base-94 header (O-FMT-18, o "byte-máximo" alternativo): [futuras-otimizacoes-formato](futuras-otimizacoes-formato.md).
- checklist do header C4: [tcf8h-header-checklist](tcf8h-header-checklist.md).
