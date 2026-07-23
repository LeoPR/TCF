# 2026-07-23-1857 — bN-dense base64 vs dict/V2-B ATUAL (v2, corrigida)

A medição que decide se a thread vale algo: contra o que o **TCF emite hoje** (não protótipo-vs-protótipo).
Dados: adult-census (`Z:/tcf-data`, REAL, 10k). Kit [`pecas.py`](../2026-07-23-1759-bn-lowcard-generaliza-e-compoe/pecas.py).

> **v1 OBSOLETA.** Reportava "8/9, k=2 → 0.17×, regra `k≤16`". A verificação `wf_71934332` **validou o
> núcleo** (comparação total-vs-total é justa — corpo-vs-corpo dá o mesmo; RT real; multi-col não muda
> nada, o TCF é colunar) **mas derrubou o enquadramento**: regra errada fora da janela, largura em
> escada, e gzip/N nunca medidos. Esta v2 corrige tudo.

## Resultado (0 falhas de RT)

**Headline honesto — tabela inteira (9 colunas, N=10k): 89.902 → 48.224 B = 1,86× menor**
(por-coluna `min(TCF, bN)`). Não o "6×" de uma coluna booleana.

| coluna | k | w | TCF | bN(exato) | razão | pós-gzip |
|---|---:|---:|---:|---:|---:|---:|
| sex / class | 2 | 1 | ~10.027 | ~1.691 | **0,17×** | 0,75–0,78× |
| race / relationship / marital-status | 5–7 | 3 | ~10.089 | ~5.085 | **0,50×** | 0,88–0,96× |
| workclass / occupation / education | 9–16 | 4 | ~10.162 | ~6.825 | **0,67×** | 0,90–1,02× |
| native-country | 41 | 6 | 9.111 | 10.369 | 1,14× (perde) | 0,79× |

## O que a v2 corrigiu (e por que importa)

- **Largura EXATA `ceil(log2 k)`** em vez da escada {1,2,4,8}: recupera até 33% (k=5/6/7 passaram de
  0,67× para **0,50×**; native-country de 1,50× para 1,14×). É o "mecanismo lógico bom".
- **Não existe limiar simples de k** — o cruzamento é NÃO-MONOTÔNICO: bN ganha em k≤32, perde em
  k≈64–94, e **volta a ganhar em k≥95** porque o dict/V2-B usa base-94 e ali pula de 1 para **2
  chars/símbolo**. Logo a regra certa **não é `if k≤16`** (erro da v1) — é **competir no FLOOR/min**.
- **gzip encolhe muito o ganho** (0,17× vira 0,75×) e inverte 1/9. O corpo do dict é texto redundante
  (gzip come); o do bN é base64 de bits densos (incompressível). Sinal, não critério — mas material.
- **N pequeno mata o ganho**: `sex` em N=5 dá 0,96× (empate); só amortiza com volume. Isso colide com
  o foco declarado em payload minúsculo — o bN compensa em **coluna grande + cardinalidade baixa**.
- **Escaping seguro** (corrige corrupção silenciosa da v1): o `\x1f` sem escape decodificava valores
  ERRADOS sem erro. Agora `\\`, `\n` e o separador são escapados; custo ~10–22 B/coluna.

## Recomendação (não executada — exige aprovação, toca `src/tcf`)

Entrar como **mais um candidato no FLOOR/`min(tcf, raw, dict, split)`** por coluna — nunca-pior em
bytes de wire por construção, sem depender de acertar limiar nenhum. É uma peça pequena e cirúrgica.
Calibragem fina (limiar, gzip-awareness, w custom) fica pro `.9`, como o owner definiu.

## Rodar / layout

```
python run.py     # 9 colunas + varredura N + cruzamento k · 0 falhas de RT
```
`outputs/<col>.bn-exato.tcfp` · `result.md`. Lê `Z:/tcf-data` (real). **Não toca `src/tcf`.**
