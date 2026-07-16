# Lab 2026-07-16-0110 — WELD P2: tipos escalares (number/bool)

**Status**: WELDED. **Ticket**: [T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md)
(P2) · [ADR-0033 §Update P2](../../../../docs/adr/0033-hierarchical-codec-weld.md).

Owner (2026-07-16) aprovou as 5 recomendações do [levantamento](../notas/p2-tipos-levantamento.md).
**Insight**: o codec recebe OBJETOS Python → o tipo é CONHECIDO (não deduzido de string ambígua) →
P2 vira **tag por-COLUNA**, limpo e RT-exato.

## Mecanismo (aditivo, L2)

| coluna (tipo dos valores Python) | armazena | tag no meta |
|---|---|---|
| **string** (default) | o valor | — |
| **number** (int/float) | `json.dumps` → `json.loads` (distingue int/float por-valor) | `n` |
| **bool** (true/false) | `true`/`false` | `b` |

- tag de 1 letra **após o size**: `idade:4n`, `ativo:5b`. **Coluna TIPADA sempre emite `:size`+tag**
  (só string-default omite size na última folha) → resolve ambiguidade `nomen` vs nome-tipo.
- compõe com null (P3a/P3b: `x?:msize:size n`, `xs#:c?:e[]:asize n`) e escapa nomes normalmente.
- `_scalar_type` deduz do Python (bool antes de int); **NaN/±Inf e tipo-MISTO = fail-loud** (P5/não-JSON).

## Evidência (rodar `python run.py`) — [outputs/00-resultado.txt](outputs/00-resultado.txt)

| etapa | resultado |
|---|---|
| **Didático** (10 formas) | RT 10/10 · headers legíveis (`idade:9n`, `x?:8:10n` nullable-number, `xs#:3?:8[]:8n` array-num-null) |
| **Realista** (pedidos: int/float/bool + cupom null + itens tipados) | RT byte-exato (283B vs 414B JSON) |
| **Massa** (fuzz 6000: colunas str/num/bool, nullable, arrays tipados) | 6000/6000 |

**Disambiguação (a assinatura P2)**: `a:4,b:5,c:4n,d:5b` — campos NOMEADOS `a`/`b` (string, sem tag)
ao lado de `c` (number) e `d` (bool). string `"30"` ≠ int `30`; string `"true"` ≠ bool `True`.

## Gate

Suíte **727 passed**, 2 skipped, 1 xfailed; flat byte-canônico intacto; **all-string byte-idêntico**
(sem tag). Fronteira fail-loud: tipo-misto (P5), NaN/Inf, array-obj-sem-chaves. Auditoria adversarial:
`wf_10194874-083` (achados dobrados no result). Ver [result.md](result.md).
