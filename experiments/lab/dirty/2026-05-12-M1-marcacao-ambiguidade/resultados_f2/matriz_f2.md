# F2 — Matriz consolidada (M1)

Sintaxes: M1-A-escape, M1-A-escape-escopo, M1-B-quote, M1-E-range, M1-C-sumida, M1-D-slice
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix
Iteracoes para timing: 1000

## Bytes UTF-8 (literais)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 162 | 162 | 162 | **149** | **149** | 162 |
| D2-emails-quote-id | 200 | 197 | 198 | **180** | **180** | 207 |
| D3-stress-substring | 242 | 233 | 233 | **206** | **206** | 218 |
| D4-caos-mix | 152 | 152 | 160 | **141** | **141** | **141** |
| **TOTAL** | **756** | **744** | **753** | **676** | **676** | **728** |

## Bytes pos-gzip (nivel 9)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | **112** | **112** | **112** | 113 | 113 | 123 |
| D2-emails-quote-id | 152 | 150 | 151 | **148** | **148** | 161 |
| D3-stress-substring | 148 | 144 | 146 | 142 | **141** | 152 |
| D4-caos-mix | **104** | **104** | 105 | 106 | 106 | 108 |
| **TOTAL** | **516** | **510** | **514** | **509** | **508** | **544** |

## Bytes pos-bz2 (nivel 9)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 132 | 132 | 132 | **128** | **128** | 133 |
| D2-emails-quote-id | 167 | 165 | 165 | 164 | **162** | 173 |
| D3-stress-substring | 167 | 163 | 159 | 163 | **158** | 169 |
| D4-caos-mix | **113** | **113** | 115 | 114 | 114 | 118 |
| **TOTAL** | **579** | **573** | **571** | **569** | **562** | **593** |

## Razao gzip (gzip/utf8) — quanto menor = ja' mais comprimido

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | **0.691** | **0.691** | **0.691** | 0.758 | 0.758 | 0.759 |
| D2-emails-quote-id | **0.760** | 0.761 | 0.763 | 0.822 | 0.822 | 0.778 |
| D3-stress-substring | **0.612** | 0.618 | 0.627 | 0.689 | 0.684 | 0.697 |
| D4-caos-mix | 0.684 | 0.684 | **0.656** | 0.752 | 0.752 | 0.766 |
| **TOTAL** | **2.747** | **2.755** | **2.737** | **3.022** | **3.017** | **3.000** |

## Tempo encode (microsegundos, mediana)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 157.2 | 199.2 | 198.1 | 258.4 | 251.6 | **38.5** |
| D2-emails-quote-id | 214.2 | 228.8 | 229.2 | 201.2 | 295.3 | **92.1** |
| D3-stress-substring | 227.9 | 242.5 | 217.3 | 310.1 | 321.6 | **86.1** |
| D4-caos-mix | 186.6 | 194.7 | 196.2 | 252.4 | 280.8 | **56.4** |
| **TOTAL** | **785.9** | **865.2** | **840.8** | **1022.0** | **1149.3** | **273.1** |

## Tempo decode (microsegundos, mediana)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 97.7 | 98.5 | 93.9 | 102.0 | **48.6** | 81.6 |
| D2-emails-quote-id | 117.0 | 120.2 | 108.6 | 122.9 | 127.5 | **97.5** |
| D3-stress-substring | 120.0 | 129.4 | 111.7 | 131.5 | 134.7 | **108.5** |
| D4-caos-mix | **44.2** | 95.7 | 92.0 | 100.2 | 102.5 | 44.3 |
| **TOTAL** | **378.8** | **443.8** | **406.1** | **456.6** | **413.3** | **331.9** |

## Tempo encode p95 (microsegundos)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 201.2 | 264.6 | 258.4 | 313.7 | 380.0 | **87.9** |
| D2-emails-quote-id | 262.8 | 312.9 | 282.7 | 333.8 | 341.3 | **98.7** |
| D3-stress-substring | 281.1 | 306.8 | 282.1 | 383.0 | 389.8 | **107.1** |
| D4-caos-mix | 246.6 | 233.3 | 236.1 | 302.1 | 360.4 | **86.4** |
| **TOTAL** | **991.7** | **1117.6** | **1059.3** | **1332.6** | **1471.5** | **380.1** |

## Tempo decode p95 (microsegundos)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | 114.5 | 136.2 | 132.2 | 109.8 | 132.0 | **109.7** |
| D2-emails-quote-id | 152.6 | 166.5 | 155.2 | 157.5 | 161.8 | **121.8** |
| D3-stress-substring | 157.7 | 170.2 | 159.6 | 171.6 | 153.3 | **147.3** |
| D4-caos-mix | 116.9 | 124.3 | 129.6 | 139.1 | 147.4 | **85.8** |
| **TOTAL** | **541.7** | **597.2** | **576.6** | **578.0** | **594.5** | **464.6** |

## Propriedades qualitativas

| Sintaxe | Encoder | Decoder | Lookahead enc | Lookahead dec |
|---|---|---|---|---|
| M1-A-escape | nao (puramente sintatico (escape char a char)) | nao (puramente sintatico) | 0 chars | 1 char apos `\` |
| M1-A-escape-escopo | nao (puramente sintatico (agrupa seq digit)) | sim (modo escape escopo apos `\` (le todos digits)) | depende do tamanho da seq de digits | K chars (K=tamanho da seq de digits) |
| M1-B-quote | nao (decide aspa por bloco inteiro) | sim (modo aspas (le ate aspa final)) | varre bloco para decidir aspas | ate aspa final (variavel) |
| M1-E-range | nao (agrupa refs consecutivas (K>=3)) | sim (modo range apos `..` (lookahead 1)) | scan da lista de refs consecutivas | 1 char apos `.` para confirmar `..` |
| M1-C-sumida | sim (mantem max_idx_visivel global) | sim (max_idx_visivel global + fallback literal se int>max) | 0 (decide por max_idx_visivel atual) | 0 (decide por max_idx_visivel atual) |
| M1-D-slice | nao (puramente sintatico) | sim (mantem eids_decodados completos para slicing) | 0 | le ate fim do slice `e:a-b` |

## Complexidade algoritmica

| Sintaxe | Encode | Decode | Latencia incremental |
|---|---|---|---|
| M1-A-escape | O(L) por linha, L=chars do literal | O(N) por linha, N=chars TCF | linha a linha |
| M1-A-escape-escopo | O(L) por linha | O(N) por linha | linha a linha |
| M1-B-quote | O(L) por linha | O(N) por linha | linha a linha |
| M1-E-range | O(R) por linha, R=num refs | O(N) por linha | linha a linha |
| M1-C-sumida | O(L) por linha | O(N) por linha | linha a linha (com contador) |
| M1-D-slice | O(R) por linha | O(N) por linha + O(b-a) por slice | linha a linha (acumula eids decodados) |

## Notas por sintaxe

- **M1-A-escape**: Mais simples. Sem estado. Custo proporcional aos chars.
- **M1-A-escape-escopo**: Decoder com modo extra ao ver `\` antes de digit.
- **M1-B-quote**: Aspa custa 2 chars; dispara por bloco com ambiguo.
- **M1-E-range**: Ortogonal a escape escopo (herdou de M1.A'). Range vence quando K>=3 sequencial.
- **M1-C-sumida**: Encoder e decoder com estado de contador. Inutil em ref-context (regra de ouro).
- **M1-D-slice**: Decoder usa O(sum(len(eid))) de memoria para suportar slice. Outros guardam so' frags individuais.
