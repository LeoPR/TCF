# Resultado — protótipo bN como candidato do min() por-coluna [probatório]

Números: `artifacts/` (`python3 run.py`). Pedido do owner: ver as possibilidades / entender se está ok.

## Veredito: a forma ENCAIXA (RT-OK), sem mudar a arquitetura do header

O par `bn_encode`/`bn_decode` roda como candidato do `min()` por-coluna com um marcador char-PREFIXO, e o
round-trip fecha. As 4 possibilidades que o owner queria ver:

### 1. O par enc/dec (`bn_codec.py`)
- `bn_encode(vals) -> bytes | None` — `None` se k>256 (não é baixa-card). Body auto-descritivo:
  `[w:1][domlen:2][domínio via tcf.encode][índices packed a w bits]`. **É irmão do dict**: domínio+índices.
- `bn_decode(body, n)` — byte-idêntico. (índices re-derivados de `vals`; no Formato A viriam do `*N|^k` do HCC.)

### 2. Slot no min() com char-prefixo (`01-ilustrativo.txt`)
Header do container: `#PROTO.BN 8 #15=ativo,#11=status,17=id` — `#`=bN, sem-prefixo=tcf. O decoder ramifica
por prefixo, self-describing. **Mesmo mecanismo** do `!`/`@`/`%` do multi-col real (`multi/core.py`).

### 3. Heterogêneo por coluna — real adult (`02-real-min-por-coluna.txt`)

| coluna | k | modo vencedor | body |
|---|---|---|---|
| sex | 2 | **# (bN, b)** | 6120B |
| race | 5 | **# (bN, b4)** | 24480B |
| education | 16 | **# (bN, b4)** | 24561B |
| age | 74 | **# (bN, b8)** | 49193B |
| fnlwgt | 28523 | **! (raw)** | 333351B |

bN vence as de baixa-card; em high-card (`fnlwgt`, k>256) **bN nem se oferece** → min fica com raw. A
fronteira k>256 é respeitada por construção. RT-OK.

### 4. Gate terminal — brotli (`03-gate-terminal-brotli.txt`)
Container sex+race+education, COM vs SEM bN:

| | pré-brotli | pós-brotli q11 |
|---|---|---|
| COM bN | 55216B | 29695B |
| SEM bN | 297713B | 42130B |
| ganho | 5.39× | 1.42× |

bN encolhe muito pré-brotli, mas o ganho cai muito pós-brotli → **candidato opt-in por "saída terminal"**.

## CAVEAT (registrado nos artefatos)

O `min()` do protótipo tem só **{tcf, raw, bN}** — **não** o **V2-B/dict** real (irmão próximo do bN, no
`fallback=True` do `src/tcf`). Logo o "SEM bN" aqui é **mais fraco** que produção, e os ganhos (5.39×/1.42×)
**superestimam** a margem real. A margem correta **bN vs V2-B** já foi medida na consolidação:
**~8/w pré-brotli** e **~1.0-1.3× pós-brotli** (colapsa). Este lab prova o **MECANISMO** (enc/dec, RT, slot no
min(), fronteira k>256, gate), não a margem-vs-V2-B.

## Está ok? (a pergunta do owner)

Sim, como **forma**: char-prefixo + `min()` + decode ramificado **já existem** no multi-col; bN é aditivo.
Para produção faltam 4 pontos (char alocado, ramo no `min()` real, par byte-idêntico, gate terminal) — e o
welding segue **gated por H-TYPE-02/03** (N<5 fontes reais + colapso sob brotli). É protótipo de possibilidade,
**não** welding candidate.

## Limites

- `min()` sem o candidato V2-B/dict (ver CAVEAT) → ganhos superestimam vs produção.
- Container é um mimético do multi-col (não o `multi/core.py` real); prova a forma, não a integração.
- 1 fonte real (adult); a margem já medida em 3 fontes na consolidação. Índices re-derivados (não do HCC).
