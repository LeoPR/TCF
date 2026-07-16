# Lab 2026-07-15-2130 — WELD P3a: null em campo (didático → realista → massa)

**Status**: weld welded, evidência inspecionável. **Ticket**:
[T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P3a) ·
[ADR-0033 §Update P3a](../../../../docs/adr/0033-hierarchical-codec-weld.md).

Owner deu o go ("pode fazer o weld e depois os experimentos") + a metodologia de datasets:
**didático → realista → massa**, RT obrigatório 120%, evidência guardada pra inspeção.

**P3a**: `null` em CAMPO de objeto — o construto JSON que faltava. Mecanismo: **estende a máscara
do P1** (o slot `0` já reservado): `.`=presente(valor) · `-`=ausente · **`0`=null (→None)**. Corpo
denso (só `.`). Distingue **null ≠ ausente ≠ `"null"` ≠ `""`**. Cobre null escalar/objeto/array +
all-null. `src/tcf/hierarchical.py` (L2, aditivo; NÃO toca o L1/`syntax.py`).

> **H-PROFILE-01**: null usa a MÁSCARA por ora; o **índice-de-substituição** (lab 2026-07-15-2101) é a
> alternativa a MEDIR sob perfil de uso — trocável na "costura" `_emit_row`/`_read_object`, sem mudar API.

## Evidência (rodar: `python run.py`) — [outputs/00-resultado.txt](outputs/00-resultado.txt)

| etapa | resultado |
|---|---|
| **(1) DIDÁTICO** (7 casos que forçam a forma) | RT 7/7 byte-exato — null escalar/objeto/array, all-null, null+ausente, 4-vias, null aninhado. Cada `outputs/01-*.tcf` + `-rt.json` diffável |
| **(2) REALISTA** (cadastro API-like, 5 reg) | RT byte-exato; tcf=601B vs json-compacto=942B |
| **(3) MASSA** (receita-cnpj, null REAL sem coerção) | RT byte-exato até 25% (12884 raízes / 50105 est / **24069 nulls reais**); full esbarra no BUG-SEQRLE (L1, não do P3a) |

**Inspeção do wire** (o que o owner pediu — dá pra LER a saída): `outputs/01-06-4-vias.tcf`:
```
#TCF.8Hstatus?:10:6,outro?:7      ← status e outro são MASCARADOS (?)
\0                                 ← máscara status: '0'(null,L1-esc) · '.'.·'.' · '-'(ausente)
*2|.
-
null                               ← coluna status (valores presentes): a STRING "null"
                                   ← e a STRING "" (linha vazia) — ≠ do null estrutural acima
...
```
→ null(None), "null"(str), ""(str), ausente — **4 vias distintas**, legíveis no formato comprimido.

## Gate

Suíte **693 passed, 2 skipped, 1 xfailed**; flat byte-canônico intacto (D1-D9/D17a/real-world);
uniforme byte-idêntico (sem `?`). Testes P3a em `tests/test_hierarchical_rt.py` (7 casos + 4-vias +
mask-`0`→null); fronteiras seguem fail-loud (null-em-elemento P3b, tipos mistos). Ver [result.md](result.md).
