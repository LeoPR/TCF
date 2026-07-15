# Lab 2026-07-14-2043 — L3: multiplicidade EXPLÍCITA vs DEDUZIDA (independência × bytes)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md) ·
[tcf-camadas-arquitetura](../notas/tcf-camadas-arquitetura.md) (L3).

Testa a hipótese do owner (2026-07-14) sobre o trade do **L3** (otimização pela
hierarquia): mesmo a hierarquia dizendo que o pai **não precisa expandir**, o
**NÚMERO** (multiplicidade) pode ser necessário. Duas formas:

- **EXPLÍCITA** (o `#count` do weld, ou a marcação `*N|`): cada bloco se basta →
  **assíncrono/paralelismo total**; a estrutura é separável do dado (lazy).
- **DEDUZIDA** (pai repete + RLE; a multiplicidade sai do run do pai): **menos bytes**,
  MAS a montagem tem que **ler o dado do pai** e agrupar → as colunas **se conversam**
  → menos independência.

## Medido (RT-exato da forma explícita = o weld)

Bytes por LARGURA do registro (nº de campos-pai `K`), 6 registros:

| K | explícita (#count) | deduzida (tabelão) | Δ | só o count | vence |
|---:|---:|---:|---:|---:|---|
| 1 | 192 | **163** | +29 | 20 | deduzida (−bytes) |
| 2 | 239 | **223** | +16 | 20 | deduzida (−bytes) |
| 4 | **333** | 343 | −10 | 20 | **EXPLÍCITA** (Pareto) |
| 8 | **521** | 583 | −62 | 20 | **EXPLÍCITA** |
| 16 | **909** | 1069 | −160 | 20 | **EXPLÍCITA** |

## Sinal-piloto (NÃO veredito — 1 eixo × 1 métrica, sintético)

> Owner: multiplicidade é **só UMA hipótese ilustrativa**, uma entre várias condições. O L3 é um
> **bloco de otimizações** (eixos: latência, memória, velocidade, compressão) a **testar em massa**.

1. **Estreito (K=1–2)**: a deduzida gastou menos bytes (economizou o count). Crossover ~K=3 neste dado.
2. **Largo (K≥4)**: a explícita gastou menos E manteve independência (a deduzida repete `*N|` em CADA
   coluna-pai; a explícita, 1 count ~20 B constante).
3. **Dependência (qualitativo)**: explícita = 1 coluna de controle minúscula (count) → dado
   independente + estrutura legível sem materializar o dado (lazy, como o `view()`). Deduzida =
   estrutura entrelaçada no dado do pai → filho depende do pai → menos assíncrono.

## O que NÃO estabelece

Só 1 eixo (largura) × 1 métrica (bytes-pré-brotli), sintético, N pequeno. Latência/memória/velocidade
não medidas, sem dado real, sem brotli a jusante. O weld usa `#count` explícito **por ora**, não por
estar "provado ótimo".

## Otimização — DEIXAR PRO FIM (owner)

- **H-L3-OPT-BLOCK**: parâmetros de L3 (multiplicidade explícita/deduzida é 1 item; outros a levantar)
  medidos nos eixos latência × memória × velocidade × compressão; talvez `min()` por documento.
  `aberta`, confiança **Baixa**. Registrar, **não implementar agora**.

## Rodar

```powershell
python experiments/lab/dirty/2026-07-14-2043-l3-multiplicidade-independencia/study.py
```

Usa o `encode_hierarchical` weldado (read-only) p/ a forma explícita; a deduzida é medida com
`encode` por-coluna. Zero mudança em `src/tcf`. Ver [result.md](result.md).
