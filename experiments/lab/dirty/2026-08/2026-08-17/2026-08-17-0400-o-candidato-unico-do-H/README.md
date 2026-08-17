# 2026-08-17-0400 — o candidato único do `.8H`

## Era / foi / é / será

- **Era**: o `.8H` foi soldado (ADR-0033) como *cliente do compressor de coluna* — cada
  folha chama `_encode_col`, o encoder single-col.
- **Foi**: o `.8M` ganhou candidatos por coluna (`raw` ADR-0022, `dict` ADR-0025,
  `split` ADR-0026) e passou a rodar `min(tcf, raw, dict, split)`. O `.8H` **não** acompanhou.
- **É**: o gap é **+23,0%** no corpus, e **100,0% dele** é essa diferença. Medido.
- **Será**: abrir o `min()` nas folhas. O header **não** é o assunto.

## A pergunta (uma só)

O `.8H` perde +23% no corpus. **É mesmo o candidato único que explica?**

Isso já tinha sido afirmado no lab [`2026-08-16-2230`](../../2026-08-16/2026-08-16-2230-avaliacao-do-H/),
mas saiu de **uma medição só**, minha. O owner pediu a contraprova antes de gastar esforço
em cima. Este lab existe para isso — e não para mais nada.

## O mecanismo, no código

| rota | como encoda uma coluna | onde |
|---|---|---|
| `.8M` | `min(tcf, raw, dict, split)` | `multi/core.py:456-470` (`_best_of`) |
| `.8H` | `_encode_col(vals, stamp=False)` — o encoder **single-col** | `hierarchical.py:491,496,502` |

O single-col tem os candidatos **dele** (polaridade, denso `b1`/`b2`, bN, nature), mas
**não** tem `raw`/`dict`/`split`. A hipótese é exatamente essa lacuna.

## Método

Para cada tabela do corpus (janela **contígua do meio**, N=2000 — a régua do lab `0530`):

1. `wire_M = encode(dict)` → rota `.8M`
2. `wire_H = encode(list[dict])` → rota `.8H`
3. Por coluna: `b_single` (o que a folha do `.8H` usa) contra `b_min` (o que o `min()`
   do `.8M` daria). O **orçamento** do candidato único é `Σ (b_single − b_min)`.
4. Comparar o orçamento com o `gap = B(wire_H) − B(wire_M)`.

O `min()` foi **reimplementado** no lab porque `_best_of` é *closure* de `_encode_multi` e
não dá para importar — com a mesma ordem e o mesmo critério (`<`, não `<=`), e com o
**mesmo** `DEFAULT_PIPELINE` que o encoder usa, para não medir outra coisa.

**Round-trip validado nos dois wires** antes de qualquer byte ser reportado (§RT).
`src/tcf` intocado. `Z:/tcf-data/` somente-leitura; nada baixado.

## Resultado

| | |
|---|---:|
| tabelas | 23 |
| total `.8M` | 2 257 869 B |
| total `.8H` | 2 777 913 B (**+23,0%**) |
| **gap** | **+520 044 B** |
| orçamento do candidato único | +520 052 B |
| **explica** | **100,0%** |
| header do `.8H` | 2 920 B = **0,11%** do wire, **0,6%** do gap |

A diferença entre gap e orçamento é de **8 bytes em 520 044** — ruído de moldura. A
hipótese não é aproximadamente verdadeira; ela é a explicação inteira.

**O header está encerrado como assunto.** Ele custa 0,6% do gap. Mesmo zerado, não move
a agulha.

## Quem faria o trabalho

| modo vencedor | colunas | bytes recuperados | % do gap |
|---|---:|---:|---:|
| `split` | 37 | 255 816 | **49,2%** |
| `dict` | 70 | 222 602 | **42,8%** |
| `raw` | 20 | 41 634 | 8,0% |
| `tcf` (já vence) | 59 | 0 | 0% |

**127 de 186 colunas (68%) ganhariam.** `split` + `dict` fazem **92%** do trabalho.

Detalhe que orienta a implementação: o `split` ganha **poucas colunas com muito byte**
(37 colunas, 49%) e o `dict` **muitas colunas com menos byte cada** (70 colunas, 43%).

### Não é concentrado

| | |
|---|---:|
| top 1 coluna | 3,0% do gap |
| top 5 | 13,6% |
| top 10 | 23,3% |
| top 20 | 38,0% |
| top 50 | 66,2% |

Não há uma coluna patológica puxando o número. O ganho é **largo** — o que sustenta que
a causa é estrutural (falta o `min()`), não um caso de borda.

As que mais pesam são todas do mesmo feitio: identificador com separador fixo
(`cnpj`, `c_phone`) ou **data ISO** (`data_abertura`, `l_shipdate`, `o_orderdate`) —
exatamente o alvo do `split` estrutural.

## O que este lab NÃO responde

- **Se abrir o `min()` nas folhas é barato ou correto.** Ele mede o *teto do ganho*, não
  o custo. A folha do `.8H` grava `size` no header e o decode fatia por ele; um candidato
  novo precisa de marcador de modo no meta da folha — e o meta do `.8H` tem gramática
  própria (`:size`, `?:mask`, `#:[`), diferente do `[!@%]<size>` do `.8M`.
- **Se os candidatos são seguros em folha aninhada.** Medi o corpo isolado de cada coluna,
  não o corpo dentro da árvore.
- **`T-UM-CAMINHO-SO`**: os dois conjuntos de candidatos são quase disjuntos; cada
  mecanismo teria de ser soldado duas vezes. Não avaliei esse custo aqui.

## Conexões

- Avaliação anterior do `.8H` (a que este lab confirma):
  [`2026-08-16-2230`](../../2026-08-16/2026-08-16-2230-avaliacao-do-H/)
- Auditoria do `.8M` no mesmo corpus: [`2026-08-16-2130`](../../2026-08-16/2026-08-16-2130-auditoria-do-M-no-corpus/)
- A régua de amostragem (janela contígua do meio): [`2026-08-15-0530`](../../2026-08-15/2026-08-15-0530-date-real-e-cpu/)
- ADRs dos candidatos: 0022 (`raw`) · 0025 (`dict`) · 0026 (`split`) · 0033 (weld do `.8H`)
