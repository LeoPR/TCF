# (a) Descapar V2-B — prototipo read-only [probatório]

**Data**: 2026-07-01. Simula remover o cap `_V2B_MAX_CARD=1024` (monkeypatch em runtime; `src/tcf`
INTOCADO) → o dict vira candidato do `min(tcf,raw,v2b,split)` também p/ high-card. Script:
[descapar_proto.py](descapar_proto.py). Output: [artifacts/run-output.txt](artifacts/run-output.txt).

## (1) Ganho de bytes (multi-col; delta≤0 = descapar melhora) — BYTE-SAFE
```
tabela                     capped    uncapped   delta     compute
br-identidades/empresas    194117    184646    -4.88%    x1.77
receita/estabelecimentos   105766    100138    -5.32%    x1.07
br-identidades/pessoas     285960    284403    -0.54%    x1.90
tpch/lineitem              301414    299806    -0.53%    x2.16
tpch/orders                336888    336888    +0.00%    x1.92   (high-card estruturado -> min pega tcf)
tpch/partsupp, customer    ...       ...       +0.00%    x1.1
adult                      101983    101983    +0.00%    x1.37
```
**delta ≤ 0 em TUDO** (min nunca regride). RT=True em todas. O ganho é **modesto e concentrado**:
−5% nas tabelas com colunas **high-card espalhadas** (municipio_id, socio_cpf, razao_social,
municipio_cod), **0%** onde as colunas high-card são estruturadas (orders/partsupp: seq-RLE ganha →
min mantém tcf) ou low-card (adult).

## (2) Pins byte-canônicos: INALTERADOS
```
D1-emails-simples  118=118   retail-description  27581=27581   retail-stockcode 11437=11437
lineitem-comment   50598=50598   D17a (multi)  303=303          TODOS IGUAIS
```
Confirmado: os gates são single-col (D1-D9, real-world) ou low-card (D17a `categoria`) → o V2-B nem
é candidato neles → **descapar não toca nenhum baseline pinado**. Weld byte-safe, sem re-pin.

## (3) Custo de compute + heurística de skip
- **Custo**: encode ~**1.1× a 2.2×** mais lento nas tabelas high-card (o dict-encode extra por coluna
  K>1024). É a razão do cap existir (evitar o sub-encode). Real e não-trivial (br pessoas 43s→81s).
- **Skip barato** (`N·w(K) ≥ tcf` → pular dict; sound, nunca pula vencedor): evita só **2/24 (8%)** —
  fraco (o stream sozinho raramente já perde; é a *tabela* que empurra o dict). **Não recupera o compute.**
- **Skip melhor (recomendado)**: reusar o sinal de estrutura que o pré-pass **já computa** —
  `detect_cadence` / run-ratio de adjacência. Colunas estruturadas (onde tcf/seq-RLE vence, dict perde)
  são exatamente as que dão +0% e pagam compute à toa → pular o dict nelas recupera a maior parte do
  ~2× **sem perder ganho** (o dict só ganha em espalhado, não-cadenciado).

## Veredito
Descapar é **byte-safe** (min; pins intactos; RT ok) e dá **−5% real** em tabelas com high-card
espalhado — o único ganho seguro que sobrou dos 3 grandes desta sessão. **Mas** o custo de compute
(~2×) é real e o skip barato não o cura; a mitigação certa é o **skip cadence-aware** (reusa o pré-pass).

**Opções de weld (owner decide; toca `src/tcf`, sob aprovação)**:
- **(A) cap-raise** (ex.: 1024→8192): captura os ganhos reais (municipio/cpf/razao K≈1.4–6k) com
  compute contido (não tenta dict em K enorme). Passo incremental de menor risco.
- **(B) descapar total + skip cadence-aware**: ganho máximo, mas exige a heurística de skip pra o
  compute não dobrar. Mais trabalho.
- **(C) descapar total sem skip**: −5% onde paga, ~2× compute nas tabelas high-card. Simples mas caro.

Recomendo **(A)** como próximo passo (baixo risco, captura o essencial), medindo se um cap ~8k já pega
os wins; **(B)** se o compute-vs-byte justificar depois. Nada bloqueia; é ganho incremental seguro.
