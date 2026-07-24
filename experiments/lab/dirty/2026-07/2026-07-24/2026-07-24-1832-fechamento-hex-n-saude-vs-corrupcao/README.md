# 2026-07-24-1832 — Fechamento: saúde do output vs corrupção (weld hex-n)

Prova a garantia do owner: *"o que for produzido pelo TCF pra encode e decode sempre será
saudável — as verificações fora só vão ocorrer por corrupção ou bug."* Duas propriedades
testadas separadamente contra o `src/tcf` real (não protótipo).

## A. SAÚDE — 127 casos, 0 falhas ✅

Fuzz amplo: N de 0 a 50.000, regimes (all-true/all-false/alternado), proporções 1–99%, runs
mistos. Todo wire que `encode` produz: decodifica sem exceção, RT exato, tipo `bool`, e — no
modo denso — o `n` hex que o encoder escreveu já é a grafia canônica que o decoder exigiria
(autoconsistência).

## B. CORRUPÇÃO — 506 mutações, 4 categorias

| categoria | qtd | classificação |
|---|---:|---|
| 1. bit-flip no payload denso | 88 | **esperado** — sem checksum de dado (limite de design) |
| 2. `n` no mesmo quantum-de-byte (all-false) | 1 | **explicado** — mesma classe (1), via header; independente de hex |
| 3. `KeyError` também no órfão puro | 42 | **pré-existente** — lacuna do core genérico, fora deste weld |
| 4. `KeyError` só no caminho tipado | **0** | seria bug novo — não ocorreu |

**0 bug de implementação NOVO introduzido pelos welds desta sessão.**

### Causa raiz do item 2 (o único "estrutural", explicada — não é falso positivo)

`n15-all-false`: flip no hex muda `n=15`→`n=9`. `ceil(15/8)` e `ceil(9/8)` são **o mesmo nº de
bytes (2)** — o check de tamanho exato não distingue `n` dentro do mesmo quantum. E como os
dados são all-false (todos zero), os bits que "viram padding" ao encolher `n` também são zero
— passam no check de padding. **Não é bug do hex**: a mesma ambiguidade existiria com `n`
decimal. É limitação de formato sem checksum, não de implementação.

### Causa raiz do item 3 (confirmada, não é do weld de hoje)

Testei o mesmo corpo malformado **sem** a tag `b` (órfão puro, código que já existia antes de
qualquer weld desta sessão) — o `KeyError` reproduz idêntico. É lacuna do `_decode_column`/HCC
genérico, que decodifica corpo malformado (linha começando com dígito, sem escape válido) com
exceção crua em vez de fail-loud. Registrado como achado à parte.

## Veredito

**Garantia do owner SUSTENTADA** para os welds desta sessão (hex-n, #4a, #4b): 0 bug de
implementação novo. Os itens 1-2 são limitação de design conhecida (sem checksum) — fechá-los
exigiria mudar o formato (CRC), decisão maior, fora de escopo aqui. O item 3 é achado
independente (core genérico), não bloqueia o fechamento do hex-n.

## Rodar / layout

```
python run.py     # 127 casos (saúde) + 506 mutações (corrupção) + inspeção de 12 wires
```
`inputs/*-fonte.json` · `outputs/*-wire.tcfp` (amostra) · `result.md`. Protótipo de teste —
**não toca `src/tcf`**.
