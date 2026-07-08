# 2026-07-07-2138 — protótipo bN como candidato do min() por-coluna

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) item 2 · design
[tipos-meta-grupo-fluxo.md](../notas/tipos-meta-grupo-fluxo.md) (H-TYPE-04) ·
[H-TYPE-02/03](../notas/roadmap-hipoteses.md). Pedido do owner: **ver as possibilidades** — um protótipo
pra entender se o par `_bN_encode`/`_decode_bN` encaixa como candidato do `min()`. NÃO toca `src/tcf`.

## Estado

- **era**: H-TYPE-04 dizia "bN encaixa no min() por-coluna" — projetado, não exercido.
- **é**: protótipo do par enc/dec + um mini-container que roda `min(tcf, raw, bN)` por coluna com marcador
  char-PREFIXO (`#`). RT-OK. bN vence baixa-card, não se oferece em high-card (k>256), gate-terminal medido.
- **será**: se avançar (gated por 02/03), alocar char + ramo no `min()` real (`multi/core.py`) + par
  byte-idêntico + gate terminal. **Protótipo, NÃO welding.**

## O que o protótipo mostra (as possibilidades)

1. **O par encaixa** — `bn_encode(vals) -> bytes|None` (None se k>256) e `bn_decode(body, n)`, body
   auto-descritivo `[w][domlen:2][domínio via tcf.encode][índices packed]`. RT byte-idêntico.
2. **Slota no min() com char-prefixo** — o header carrega o modo por coluna:
   `#PROTO.BN 8 #15=ativo,#11=status,17=id` (`#`=bN, sem prefixo=tcf), decoder ramifica por prefixo. Igual
   ao mecanismo `!`/`@`/`%` do multi-col real (`multi/core.py`).
3. **Heterogêneo por coluna** (adult): sex/race/education/age → `#` (bN vence); fnlwgt (k=28523>256) → `!`
   (bN não se oferece, min fica com raw). A fronteira k>256 é respeitada.
4. **Gate terminal** (sex+race+education): oferecer bN encolhe 5.39× pré-brotli, mas só 1.42× pós-brotli →
   bN deve ser opt-in por "saída terminal".

## CAVEAT importante (honestidade)

O `min()` deste protótipo tem só **{tcf, raw, bN}** — **NÃO** o candidato **V2-B/dict** real (que vive no
`fallback=True` de `src/tcf`, e é o irmão mais próximo do bN). Logo o baseline "SEM bN" aqui é **mais fraco**
que o de produção, e os ganhos (5.39× pré / 1.42× pós) **superestimam** a margem real do bN. A margem correta
(bN vs V2-B) já foi medida na consolidação: **~8/w pré-brotli** e **~1.0-1.3× pós-brotli** (colapsa). Este lab
prova o **MECANISMO** (enc/dec, RT, slot no min(), gate), não a margem-vs-V2-B.

(bN aqui re-deriva os índices de `vals`; o Formato A os pegaria do ref-stream `*N|^k` do HCC — mesmo resultado.)

## Arquivos

- `bn_codec.py` — `bn_encode`/`bn_decode` + `container_encode`/`decode` (min tcf/raw/bN + marcador prefixo).
- `run.py` — ilustrativo + real + gate-brotli. **Rodar com `python3`** (tem brotli): `python3 run.py`.
- `artifacts/` — `00-resumo` · `01-ilustrativo` · `02-real-min-por-coluna` · `03-gate-terminal-brotli`.

## Como rodar

```
python3 experiments/lab/dirty/2026-07-07-2138-bn-candidato-min-prototipo/run.py
```
(`python3` = Windows Store 3.13, tem `brotli`; `python` local não tem. `src/tcf` importado via sys.path.)

## Escopo

Dirty (protótipo de possibilidade). NÃO toca `src/tcf`. Gated por H-TYPE-02/03 (N<5 fontes + colapso brotli).
