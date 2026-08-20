# 2026-08-17 — a teoria do `split`, e o magic aninhado que dá pra tirar

**[probatório onde diz medido.]** Duas perguntas do owner ao abrir a evidência do lab 1200.

---

## 1. Qual era a teoria do `split`?

Fonte: [ADR-0026](../../../../docs/adr/0026-structural-split-weld.md) (accepted 2026-06-14),
caracterizado no lab `2026-06-14-datetime-nature-caracterizacao`.

**A observação de origem foi um acidente.** Investigavam por que colunas DATETIME ganhavam no
V2-D (que acabou refutado) e caíram num efeito muito maior e mais geral:

> **valor estruturado** (decimal, data, datetime, CPF/CNPJ) é uma sequência de **grupos de
> dígitos separados por não-dígitos**.

Se **todos** os valores compartilham o **mesmo template**, os grupos de dígito viram
**colunas-campo independentes** — e cada campo tende a **baixa cardinalidade**: fração
`.00`–`.99`, mês `1`–`12`, ano quase-constante.

**O motor não é o `split` sozinho — é a sinergia `split` → `dict`.** O split só reorganiza; quem
esmaga é o V2-B ([ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md))
aplicado a cada campo já separado. Por isso o slot split é literalmente um multi-col aninhado:
cada campo volta a passar pelo `min(tcf, raw, dict)`.

**Números do weld**: **19,39% weighted** em 8 datasets reais (50,4% nas colunas afetadas) — o
maior lever do ciclo 0.7, acima do V2-B isolado (13,9%).

**O gate é deliberadamente rígido**: template 100% uniforme, ≥2 campos, e variação real em
algum campo. Sem mecanismo de exceção — o refinamento mediu **1 near-miss em 80 colunas reais**
e concluiu que não valia a complexidade. Mistura cai no fallback.

E **complementa as natures em vez de subsumir**: no CPF a nature vence (34 038 contra 58 148 do
split); no CNPJ o split vence (32 668 contra 53 827 da nature). Quando os dois aplicam, `min()`.

Isso liga direto ao lab do CEP: o **D6** (`−19,8%`) é o mesmo mecanismo aplicado à mão —
separar o dígito de região faz os restos colidirem, e o `dict` colhe. O CEP mascarado já era um
caso de split; o D6 mostrou que dá pra ir um nível além do que o gate automático faz.

---

## 2. O magic aninhado dá pra tirar? **Dá — e há mais junto**

O owner: *"a tag TCF que aparece a segunda vez me parece muito simples de remover sem quebrar a
semântica."* Confirmado na fonte, e o alcance é maior.

### O magic não é load-bearing

```python
# src/tcf/multi/split.py
sub = body_bytes[start + ntmpl:]        # :81  a fronteira JA' vem do ntmpl
ftable = _decode_multi(sub.decode())    # :82  SO' AQUI o magic e' lido
fields = [ftable[f"c{k}"] for k in range(nf)]   # :83
```

A **fronteira do sub-table já está determinada** por `ntmpl` + o `size` do slot no meta externo.
O `#TCF.8M` existe apenas porque `_decode_multi` é ponto de entrada **genérico** e re-parseia a
assinatura. Em contexto de slot split, ela é redundante por construção.

### E os nomes `c0,c1,…` também

A linha `:83` mostra que os nomes são **sempre** `c0..c{nf-1}`, e `nf` vem do template
(`len(partes)-1`). São tão dedutíveis quanto o magic. A API **já tem** `drop_names=True` para
coluna anônima ([ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md)).

### O tamanho — medido em 45 colunas reais que o split vence

| | bytes |
|---|--:|
| slots split, total | 354 170 |
| magic (`#TCF.8M` × 16 medidos) | 112 |
| nomes `=cN` | 162 |
| **dedutível** | **274 (0,08%)** |

Por coluna, exemplos:

| coluna | slot | dedutível | % |
|---|--:|--:|--:|
| `online_retail.InvoiceDate` | 940 | 31 | **3,30%** |
| `lineitem.l_quantity` | 2 231 | 13 | 0,58% |
| `orders.o_orderdate` | 6 254 | 16 | 0,26% |
| `cep mascarado` | 164 493 | 13 | 0,01% |

### O veredito honesto

**Está certo que dá pra tirar, e está errado esperar ganho de byte.** São **0,08%** no agregado
— e a razão é estrutural: o custo é **fixo por coluna** (7 B + ~3 B por campo), enquanto o slot
cresce com `n`. Só aparece em coluna **curta**: 3,30% no `InvoiceDate` (940 B), 0,01% no CEP
(164 KB).

Isso o põe exatamente na diretriz do
[foco byte-a-byte em payload minúsculo](../../../../ROADMAP.md) — onde 3% de uma coluna de
940 B importa — e **fora** de qualquer argumento de compressão em volume.

**O argumento mais forte não é byte, é coerência de formato**: um sub-table que se re-anuncia
com a assinatura do formato inteiro contradiz a materialização minimal (*"grava só o
estritamente necessário, o resto deduz"*). O mesmo raciocínio que fez o `#TCF.8M` perder o
espaço antes do `M` (ADR-0029, ~2 B/multi).

### O que eu **não** medi

- **Custo de implementação.** Tirar o magic exige um ponto de entrada `_decode_multi_sem_magic`
  (ou um parâmetro), e isso toca `multi/core.py` — que é caminho crítico do `.8M`, com gates
  byte-canônicos pinados. Não é edição local.
- **Se re-pina baseline.** Muda o wire de toda coluna que usa split → `D17a` e real-world
  provavelmente mudam. Precisa de ADR e re-pin conscientes.
- **A interação com o `drop_names`**: se o sub-table já pudesse ser emitido com
  `drop_names=True`, parte dos 162 B cairia **sem tocar no decoder** — não testei se o
  `_encode_multi` do split aceita esse flag hoje.
- **Só bytes, sem CPU.** Um ponto de entrada sem magic pode até simplificar o parse; não medi.

**Encaminhamento sugerido**: é assunto de `.9` (limpeza/reorganização com blocos legíveis pro
port), não do `.8` — mas o `drop_names` no sub-table é a metade barata e vale checar antes.

## Conexões

- [ADR-0026](../../../../docs/adr/0026-structural-split-weld.md) (split) ·
  [ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) (dict, o motor) ·
  [ADR-0029](../../../../docs/adr/0029-version-format-identification-semi-implicit.md) (`drop_names`)
- `src/tcf/multi/split.py:58-90` (o decoder que mostra a dedutibilidade)
- Lab do CEP onde a pergunta surgiu: [`1200`](../../2026-08/2026-08-17/2026-08-17-1200-cep-real-receita/)
