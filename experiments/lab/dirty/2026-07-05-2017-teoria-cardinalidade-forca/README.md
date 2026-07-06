# 2026-07-05 20:17 — Teoria de cardinalidade: força + rápido-vs-pleno [probatório]

**Peça 8** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
teoria em [notas/teoria-cardinalidade.md](../notas/teoria-cardinalidade.md) ·
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). Auto-contido: `theolib.py` +
`tcf`. `python run.py` regenera. **Didático + MEDIDO** (a favor da teoria, não de performance).

## As perguntas (do owner)

1. **Rápido vs pleno**: uma 1:N (vinda do JSON) permite um **RLE rápido** do pai. Mas o **OBAT/HCC pleno**
   pega redundância **inter-item** (afixo compartilhado entre itens) que o RLE perde. Mesmo RT, trade
   velocidade↔razão. Quando cada um vence?
2. **Força**: o que é cardinalidade **forte / fraca / quase / induzida**?

## Seção 1 — rápido (RLE valor-inteiro) vs pleno (OBAT/HCC) — `01-rapido-vs-pleno.txt`

| coluna | RÁPIDO (RLE) | PLENO (OBAT/HCC) | quem vence |
|---|---|---|---|
| email `@empresa.com` compartilhado | 67 B | **48 B** | **pleno** (fatora o afixo inter-item) |
| ids opacos (alta entropia) | **30 B** | 39 B | **rápido** (OBAT super-tokeniza → o rápido é menor E mais rápido) |

O pleno mostra `*2|leonard*o*@empresa.com` (reusa `@empresa.com` entre pessoas). **Confirma o insight**: o
inter-item só o pleno pega — mas nem sempre o pleno ganha (em alta entropia o rápido domina).

## Seção 2 — força de cardinalidade — `02-forca-cardinalidade.txt`

| classe | critério | exemplo | medida |
|---|---|---|---|
| **FORTE** | alta multiplicidade + valor largo | email repetido 4× | mult=4.0 larg=18.3 |
| **FRACA** | pai quase não repete (mult~1) | `cliente_000..011` | mult=1.0 |
| **QUASE** | FD aproximada (g3>0) | cpf→nome c/ 1 linha suja | g3=0.167 |
| **INDUZIDA** | o JSON já dita (g3=0 por construção) | array-de-objetos | exata de graça |

## ACHADO-CHAVE — cardinalidade ≠ compressibilidade (eixos ORTOGONAIS)

A **FRACA** acima deu full **42B** << fast **144B** — mas o ganho é do **afixo `cliente_`** (compressibilidade),
**não** da cardinalidade (multiplicidade=1, nada a normalizar). Ou seja:

> **CARDINALIDADE** (multiplicidade → normalização/RLE do valor-inteiro) **≠** **COMPRESSIBILIDADE**
> (afixo/inter-item → OBAT/HCC). São **eixos ortogonais**.

Matriz 2×2 (o que cada estratégia pega):

| | inter-item SIM (afixo/dict) | inter-item NÃO |
|---|---|---|
| **cardinalidade forte** (mult alta) | pleno ganha muito (email repetido + domínio) | rápido basta/ganha (ids repetidos opacos) |
| **cardinalidade fraca** (mult~1) | pleno ganha **por afixo**, não por cardinalidade (`cliente_`) | nada ganha (aleatório único) |

O trade **rápido↔pleno** é sobre **qual redundância explorar** (cardinalidade só, vs cardinalidade+afixo),
não sobre a força. E o **mesmo RT** vale nos dois.

## Estado

- **É**: medido o trade rápido-vs-pleno + a taxonomia de força; achado da ortogonalidade.
- **Será**: registrar hipóteses (H-CARD-*) + a agenda de pesquisa (ver teoria-cardinalidade.md); FD
  aproximada real-world; o custo real de encode (velocidade) — aqui só bytes.

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
