# 2026-07-23-1857 — bN-dense base64 vs o encoder ATUAL (dict/V2-B) — dados REAIS

A medição que decide se esta thread vale algo. Tudo antes comparou protótipos ENTRE SI; aqui é contra
o que o **TCF emite hoje**. Dados: adult-census (`Z:/tcf-data`, REAL, amostra 10k), 9 colunas low-card.
Kit [`pecas.py`](../2026-07-23-1759-bn-lowcard-generaliza-e-compoe/pecas.py) (lab 1759).

## A aritmética prevista (e confirmada)

O **dict/V2-B base-94 gasta ~1 char por símbolo, independente de k**. O **bN empacota `log2(k)` bits e
só então vira base64** (6 bits/char) → `w/6` char por símbolo. Logo bN ganha enquanto **w<6 (k≤16)** e
perde em **w=8 (k>16)**. Cruzamento previsto: k=16.

## Resultado (9/9 RT ✅, total-vs-total self-contained)

| k / w | colunas | razão bN/TCF | Δ |
|---|---|---|---|
| **k=2 / w=1** | sex, class | **0,17×** (≈6× menor) | −8.334, −8.337 |
| **k=5..16 / w=4** | race, relationship, marital-status, workclass, occupation, education | **0,67×** (1,5× menor) | ≈ −3.340 cada |
| k=41 / w=8 | native-country | 1,50× (**perde**) | +4.594 |

**bN-dense vence 8/9.** O modo do TCF era `dict` em todas as vencidas (e `tcf` na k=41). O ganho é
**maior quanto menor a cardinalidade** — e k=2 é o caso bool/flag/status, comuníssimo em dado real.

## Por que isto importa

- **Regra de decisão trivial e determinística**: usar bN quando `width_for(k) < 6` (⟺ **k≤16**), senão
  o que já existe. Sem máquina de segmentos (que o [reality-check 1832](../2026-07-23-1832-reality-check-lowcard-dados-reais/)
  derrubou), sem parâmetro a calibrar.
- **Encaixa no que já existe**: é **mais um candidato** no FLOOR/`min(tcf, raw, dict, split)` por
  coluna — nunca-pior por construção. Mecanismo LÓGICO bom agora; calibragem fina fica pro `.9`.

## Ressalvas honestas

(a) O protótipo embute o domínio com separador `\x1f` **sem escaping** e header simples — um weld real
precisa de gramática/escaping próprios, o que muda alguns bytes. (b) Medido só em adult-census (9
colunas, amostra 10k). (c) Só **bytes** — não mede latência/CPU. (d) Cada coluna foi encodada como
tabela de 1 coluna; num multi-col real o framing amortiza diferente (o ganho de CORPO deve se manter,
o total não exatamente). (e) O dict/V2-B tem virtudes não capturadas aqui (ex. dicionário legível).

## Rodar / layout

```
python run.py     # 9 colunas · 0 falhas de RT · bN vence em 8/9
```
`outputs/<col>.bn-dense.tcfp` (protótipo) · `outputs/<col>.tcf-atual.tcf` (o que o TCF emite hoje) ·
`result.md`. Lê `Z:/tcf-data` (real). **Não toca `src/tcf`.**
