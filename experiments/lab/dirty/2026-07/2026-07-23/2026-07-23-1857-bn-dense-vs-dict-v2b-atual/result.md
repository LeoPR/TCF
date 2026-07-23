# bN-dense vs dict/V2-B ATUAL — v2 CORRIGIDA (pós-verificação wf_71934332)

v1 OBSOLETA (regra `k<=16` errada fora da janela; largura em escada; gzip e N não medidos). Aqui: largura EXATA `ceil(log2 k)`, escaping seguro, **gzip**, **varredura de N**, cruzamento real de k, e o agregado da TABELA INTEIRA. Comparação total-vs-total self-contained.

## 1. Colunas reais (N=10000) — cru e pós-gzip

| coluna | k | w escada | w exato | TCF | modo | bN(escada) | bN(exato) | razão exato | TCF gz | bN gz | razão gz | RT |
|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|:---:|
| sex | 2 | 1 | 1 | 10026 | dict | 1692 | 1692 | 0.17× | 1665 | 1255 | 0.75× | ✅ |
| class | 2 | 1 | 1 | 10028 | dict | 1691 | 1691 | 0.17× | 1473 | 1144 | 0.78× | ✅ |
| race | 5 | 4 | 3 | 10072 | dict | 6736 | 5068 | 0.50× | 1531 | 1472 | 0.96× | ✅ |
| relationship | 6 | 4 | 3 | 10086 | dict | 6742 | 5074 | 0.50× | 3638 | 3190 | 0.88× | ✅ |
| marital-status | 7 | 4 | 3 | 10108 | dict | 6780 | 5112 | 0.51× | 3209 | 2900 | 0.90× | ✅ |
| workclass | 9 | 4 | 4 | 10106 | dict | 6776 | 6776 | 0.67× | 3030 | 3095 | 1.02× | ✅ |
| occupation | 15 | 4 | 4 | 10222 | dict | 6885 | 6885 | 0.67× | 5590 | 5056 | 0.90× | ✅ |
| education | 16 | 4 | 4 | 10159 | dict | 6815 | 6815 | 0.67× | 4804 | 4653 | 0.97× | ✅ |
| native-country | 41 | 8 | 6 | 9111 | tcf | 13705 | 10369 | 1.14× | 2388 | 1886 | 0.79× | ✅ |

## 2. Agregado da TABELA INTEIRA (9 colunas, N=10000)

- TCF atual, tabela completa: **89902 B**
- por-coluna `min(TCF, bN-exato)` (o FLOOR proposto): **48224 B** → **0.536×** (1.86× menor)

Este é o número honesto de headline — não o 0.17× de uma coluna booleana.

## 3. Varredura de N — o ganho DESAPARECE em payload pequeno

| coluna | N=5 | N=10 | N=20 | N=100 | N=500 | N=2000 | N=10000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| sex | 0.96× | 0.69× | 0.54× | 0.33× | 0.20× | 0.18× | 0.17× |
| race | 0.73× | 0.66× | 0.74× | 0.73× | 0.56× | 0.51× | 0.50× |

**Crítico**: o ganho é assintótico em N. Em payload minúsculo (foco declarado do projeto) ele some — o domínio embutido e o header não amortizam.

## 4. Cruzamento real de k (sintético uniforme, N=10000)

| k | w exato | TCF | modo | bN(exato) | razão |
|---:|---:|---:|:---:|---:|---:|
| 2 | 1 | 10025 | dict | 1690 | 0.17× |
| 4 | 2 | 10030 | dict | 3368 | 0.34× |
| 8 | 3 | 10030 | dict | 5052 | 0.50× |
| 16 | 4 | 10041 | dict | 6760 | 0.67× |
| 17 | 5 | 10041 | dict | 8433 | 0.84× |
| 32 | 5 | 10042 | dict | 8508 | 0.85× |
| 64 | 6 | 10042 | dict | 10332 | 1.03× |
| 94 | 7 | 10042 | dict | 12150 | 1.21× |
| 95 | 7 | 20042 | dict | 12155 | 0.61× |
| 128 | 7 | 20026 | dict | 12320 | 0.62× |
| 256 | 8 | 20026 | dict | 14628 | 0.73× |

**A regra `k<=16` da v1 estava errada**: o dict/V2-B usa base-94, então gasta 1 char/símbolo só até k=94; a partir de k=95 pula pra 2 chars/símbolo e o bN volta a ganhar. Não há um limiar simples — por isso a decisão certa é **competir no FLOOR/min**, não um `if k<=16`.

## Conclusão corrigida

- **O ganho existe e é real**, mas o headline honesto é o agregado da tabela (**1.86× menor**), não o 6× de uma coluna booleana em N grande.
- **gzip inverte 1/9 colunas**: o corpo do dict é texto redundante (gzip come), o do bN é base64 de bits densos (incompressível). Sob transporte comprimido o ganho encolhe muito ou vira perda. Pela filosofia do projeto gzip é sinal, não critério — mas ignorá-lo seria desonesto num formato cujo alvo inclui transmissão.
- **Em payload minúsculo o ganho some** (N=5 ≈ empate) — e esse é o foco declarado. O bN compensa em coluna GRANDE e cardinalidade baixa.
- **A regra certa NÃO é um limiar de k**: é entrar como **mais um candidato no FLOOR/min** por coluna, que já é o padrão do TCF — aí é nunca-pior em bytes de wire por construção, sem depender de acertar limiar nenhum.
- **Largura exata importa**: `ceil(log2 k)` em vez da escada {1,2,4,8} recupera até 33% (k=5/6/7) — é o 'mecanismo lógico bom' antes de qualquer otimização fina.

**9 colunas + varreduras · 0 falhas de RT.** Regenera: `python run.py`.