# M5 — Pilha M2.A + M4.C1' (teste de ortogonalidade)

**Data**: 2026-05-14
**Estado**: foi (fechado apos confirmacao empirica)
**Sucede**: [M2.A](../2026-05-13-M2-redundancia-entre-linhas/),
[M4.C1'](../2026-05-13-M4-desfragmentacao-arvore/)
**Vem de**: decisao no [`../README.md`](../README.md) — combinar
M2.A + M4.C1' em uma pilha para testar ortogonalidade. Se aditivo,
ambos vao para o protótipo.

## Pergunta

M2.A (alias de tupla com preambulo) e M4.C1' (subseq com idx
implicito inline) capturam padroes diferentes ou os mesmos?

- **Hipotese H1 (aditivo)**: combinacao gera ganho ~ M2.A + M4.C1' =
  -1.5% + -5.9% = -7.4% vs M1.E
- **Hipotese H2 (dominado)**: M4.C1' subsume M2.A; combinacao ~
  M4.C1' alone = -5.9% vs M1.E

## Analise algebrica (antes de codar)

Para uma tupla de Lr chars usada R vezes:

**M2.A** (preambulo + uso):
- Decl `$N=tupla\n`: `Lr + 3 + len(N)` chars
- Uso `$N`: `1 + len(N)` chars (substitui Lr chars)
- Economia total: `R*(Lr - 1 - len(N)) - (Lr + 3 + len(N))`

**M4.C1'** (def inline + uso):
- 1a `~tupla~`: `Lr + 2` chars (vs Lr originais → +2)
- Uso `&N`: `1 + len(N)` chars
- Economia total: `(R-1)*(Lr - 1 - len(N)) - 2`

**Diferenca (M2.A - M4.C1')**:
```
[R*(Lr-1-len(N)) - (Lr+3+len(N))]
- [(R-1)*(Lr-1-len(N)) - 2]
= (Lr-1-len(N)) - (Lr+3+len(N)) + 2
= -2 - 2*len(N)
```

**Para qualquer R, Lr, e len(N) ≥ 1: M2.A economiza 4-6 bytes
MENOS que M4.C1' para o mesmo padrao.**

**Conclusao algebrica**: M4.C1' DOMINA M2.A para qualquer pattern.
Hipotese esperada: H2 (dominado).

## O que o experimento prova

Mesmo com algebra apontando dominacao, rodar empiricamente:

1. Confirma o teorema na pratica (RT OK)
2. Mostra se algum caso de canto rompe a dominacao (e.g. limitacoes
   do greedy fazendo M2.A "pegar" algo que M4.C1' nao pegou)
3. Documenta que M2.A NAO vai pro protótipo

## Estrutura

```
M5-pilha-M2A-M4C1p/
  data/                         (D1-D4 canonicos copiados)
  M1-E-range-baseline/          (referencia)
  M2-A-alias-tupla/             (referencia)
  M4-C1p-batch-subsequencias/   (referencia)
  M5-A-pilha-hibrida/           (detector que considera ambos custos)
  resultados/                   (matriz consolidada)
  notas/                        (analise pos-rodagem)
```

## M5.A — detector hibrido (unico micro)

Mecanica:
1. Coleta TODAS as sub-tuplas contiguas (K >= 2) de cada run.
2. Para cada candidata, calcula net sob AMBAS sintaxes (M2.A e M4.C1').
3. Seleciona o de maior net global; aplica como aquele tipo de alias.
4. Repete sobre runs modificadas (greedy iterativo).
5. Serializa: aliases M2.A vao para preambulo (`$N=...`); aliases
   M4.C1' ficam inline (`~...~` def + `&N` uso).

Decoder aceita AMBOS prefixos coexistindo.

## Resultados

| Sintaxe | D1-D4 total | delta vs M1.E |
|---|---:|---:|
| M1.E (baseline) | 676 | 0 |
| M2.A alone | 666 | -10 (-1.5%) |
| M4.C1' alone | 636 | -40 (-5.9%) |
| **M5.A (detector hibrido)** | **636** | **-40 (-5.9%)** |

RT 16/16 OK. M5.A == M4.C1' em CADA dataset (138/174/196/128).

Detalhes: [`resultados/matriz_comparativa.md`](resultados/matriz_comparativa.md).

## Conclusao

**Hipotese H2 confirmada empiricamente**: M4.C1' subsume M2.A.

Detector hibrido NUNCA selecionou alias tipo M2.A. TCFs gerados
sao identicos aos M4.C1' alone — zero `$N=...` no preambulo.

**M2.A nao vai para o protótipo.** Algebra: M2.A perde por
`2 + 2*len(N)` bytes/alias independente de R e Lr. Detalhes:
[`notas/conclusoes_M5.md`](notas/conclusoes_M5.md).
