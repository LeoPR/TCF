# Sub-exp 12 — IP variante D (hex 8-char) — report

**Data**: 2026-05-24
**Hipotese inicial**: hex 8-char (8 chars) fica entre B (base94 6c) e
C (padded 12d) em compressao.

## Resultado consolidado (A/B/C de sub-exp 09 vs D deste)

| Dataset | A (M10) | B (base94 6c) | C (padded 12d) | D (hex 8c) | Vencedor |
|---|---:|---:|---:|---:|---|
| D-IP-uniform | 18159 | **7607** | 14652 | 11253 | **B** |
| D-IP-subnet | 15747 | 6683 | **229** | 10671 | **C** (-98%) |
| D-IP-mixed | 19003 | **13075** | 16968 | 15186 | B |
| D-IP-corrupt | 18131 | **8081** | 14771 | 11585 | B |
| D-IP-edge-single | 18 | **7** | 14 | 12 | B |
| D-IP-edge-allsame | 24 | **13** | 20 | 18 | B |
| D-IP-edge-allcorrupt | **17249** | 17953 | 17953 | 17953 | A |
| D-IP-extra-large10k | 175734 | **76196** | 146412 | 112616 | B |
| D-IP-extra-hostile | 13026 | **11145** | 12464 | 11718 | B |

## Analise

### Hipotese confirmada parcialmente

D (hex 8-char) tipicamente fica entre B (denser base94 6c) e C (longer
padded 12d) em ratio — comprimento intermediario gera compressao
intermediaria. Consistente com expectativa.

### D nao domina em lugar nenhum

D nunca eh o **vencedor unico**. Sempre dominada por B (mais densa)
ou C (em subnet onde digital incremental visivel).

### Surpresa: D NAO captura subnet bem

- C subnet: 229B (1.71%) — HCC seq-RLE explode em digit-only
  incremental (`057012140000` -> `001`...)
- D subnet: 10671B (80%) — HCC capta apenas 7 runs (vs 11 em C)

**Hipotese pra esta diferenca**: HCC seq-RLE em near-identical funciona
melhor em **digit-only** strings. Hex tem transicoes char->letter
(`c0a80109` -> `c0a8010a`) que **podem quebrar** o algoritmo de
shift_escape_digits (que so' opera em digit runs).

Verificacao: `hcc_seqrle.py:96 shift_escape_digits` opera EXPLICITAMENTE
em runs `[0-9]+` (digit). Em hex, transicao 9->a sai do range digit, eh
tratada como literal -> quebra near-identical.

**Confirmado**: D nao escala como C por design do HCC seq-RLE (que e'
digit-centric).

### Implicacao academica

Owner propos "IP em hex" como alternativa byte-level. Resposta:
**conceitualmente correto, empiricamente inferior** porque:

1. Hex (8 chars) > base94 (6 chars) — denser em base94 wins em random
2. Hex (8 chars) > 4-byte binario, mas binario problematico em TCF
   textual (chars 0-31 reservados, 128-255 viram 2 bytes UTF-8)
3. HCC seq-RLE atual eh digit-centric — letras de hex impedem
   exploracao completa de cadence

### Avaliacao byte-level "4 bytes ou 8 bytes hex"

| Encoding | Chars | Por que NAO usar em TCF textual |
|---|---|---|
| 4 bytes binario (Latin-1) | 4 chars (raw) | Chars 0-31 = control reservados; 128-255 = UTF-8 2-byte = 8 bytes finais |
| 4 bytes binario (escaped) | ~6-10 chars | Escape overhead = perde compactacao |
| 8 chars hex (D) | 8 chars | Funciona OK mas perde pra base94; HCC seq-RLE digit-centric |
| **6 chars base94 (B)** | 6 chars | Vencedor empirico — mais denso, RT OK |
| 12 chars padded (C) | 12 chars | Vence subnet por digit-only cadence |

**Recomendacao**: B (base94) eh vencedor geral; C (padded) so' em
subnet. D (hex) abandonada.

## Outputs visiveis (auditoria)

`out_tcf/`:
- D-IP-*.tcf (9 datasets encoded)
- D-IP-*-pretx-sample20.txt (primeiras 20 strings hex)
- D-IP-*-decoded-sample15.txt (RT check)
- (zero mismatches.txt — RT 100% em todos)

## Conclusao

Variante D **abandonada**. Lessons:
1. Encoding mais curto = melhor compressao em datasets random (B vence)
2. Encoding com digit-only cadence visivel = melhor em subnets (C vence)
3. Hex (D) intermediario, nunca vence — perde por ambos lados
4. HCC seq-RLE atual eh digit-only (`shift_escape_digits` limitada);
   estender pra alfabetos custom seria projeto futuro mas baixo ROI

Owner question RESPONDIDA: hex eh **opcao valida mas suboptima**.
Base94 (B) e padded (C) cobrem casos diferentes melhor.

## Hipotese decorrente: HCC seq-RLE com alfabetos generalizados

Se HCC seq-RLE fosse generalizada pra qualquer alfabeto base-N (nao so'
0-9), variante D poderia atingir compressao similar a C em subnets.
Investimento alto vs ganho incerto (B base94 ja' eh quase otimo em
random). Registrada como direcao adiada.
