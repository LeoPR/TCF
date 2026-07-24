# 2026-07-24-0253 — O marcador de modo `~` é necessário, ou a ausência é inferível?

Responde à pergunta do owner, que separou **duas coisas**: (1) a DECISÃO de modo (core/RLE vs denso
bN vs misto) = a heurística FLOOR ([ticket T-TYPED-SINGLECOL-MODE-HEURISTIC](../../../../../tickets/T-TYPED-SINGLECOL-MODE-HEURISTIC.md));
(2) a GRAMÁTICA da simplificação/inferência = **este lab**: o `~` precisa estar escrito, ou a ausência
pode ser entendida como implícita?

## Três gramáticas candidatas (corpo tipado de bool)

- **G1** `#TCF.8b~<n>\n<base64>` — marcador `~` explícito + `n` no header (denso); core = sem `~`.
- **G2** `#TCF.8b<n>\n<base64>` — sem `~`, deduz modo por dígito no header.
- **G3** `#TCF.8b\n<base64(n|bits)>` — sem `~` e sem `n` no header; `n` embutido, modo deduzido por FORMA.

## Resultado (o `~` É necessário)

**Duas descobertas medidas:**

1. **O modo NÃO é sempre distinguível pela forma** — 2 colisões: o corpo core de bool pequeno é
   alfabeto base64 puro, indistinguível de um payload denso:
   - `[True]` → core `'true\n'` — `t,r,u,e` ∈ base64.
   - `[False]` → core `'false\n'` — `f,a,l,s,e` ∈ base64.

2. **`n` do denso não é dedutível** — o bit-pack tem 0-7 bits de padding, então B bytes → `n ∈
   [8(B-1)+1, 8B]` (8 valores). O `n` **tem que viajar** (no `~<n>` do G1 ou embutido no G3).

**Prova decisiva (§4)** — forçando o modo core nas colisões:

| grafia | `#TCF.8b\ntrue\n` | resultado |
|---|---|---|
| **G3** (deduz forma) | lê `true` como base64 | ❌ **corrompe** (2/8) |
| **G1** (`~`) | core = sem `~`, inambíguo | ✅ 8/8 |

## Resposta

**A ausência do marcador NÃO pode ser sempre entendida como implícita** — porque `true`/`false` são
base64-limpos e colidem com o payload denso. Resolver por "denso só quando vence (nunca nos N pequenos)"
**acopla a gramática à heurística** — mistura exatamente as duas coisas que o owner pediu pra separar, e
é frágil.

**O caminho limpo (assimetria elegante)**: a implicitude fica no **modo core (A) = o default sem
marcador**, deduzido por exclusão (como o header). O **modo denso (B) = exceção opt-in que se declara
com `~`**. Implícito = o comum; explícito = o desvio. Consistente com o resto do formato. O `~` carrega
os dois bits de informação que o denso precisa (modo + `n`).

## Escopo / limite

Bool `w=1`, N pequeno/moderado, sintético. A colisão é específica de valores base64-limpos curtos
(vale pra bool `true`/`false`; number/string teriam suas próprias colisões a checar). Protótipos
lab-local. **Nada em `src/tcf`** — é estudo de gramática pra decidir antes do weld #4.

## Rodar / layout

```
python run.py     # 8 datasets · 4 seções (formas, n, RT das 3 gramáticas, teste decisivo)
```
`inputs/*-fonte.json` · `intermediates/*.tcfp` (as 3 gramáticas por dataset) · `result.md`.
