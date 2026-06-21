# Algoritmos do TCF — documentação técnica

Documentação oficial dos algoritmos canônicos do TCF v0.7. Cada
arquivo explica:
- **O que é** o algoritmo (linguagem natural)
- **Como funciona** (sub-linguagem matemática)
- **Por que tem esse nome** (etimologia das siglas)
- **Diferencial vs literatura** (citações de trabalhos relacionados)
- **Onde se encaixa** no pipeline do TCF

## Pipeline TCF

```
Lista de strings (uma coluna de dados tabulares)
       ↓
   OBAT (camada 1: tokenização)        ← Online Bidirectional Affix Tokenizer
       ↓ tokens raiz
   HCC (camada 2: compactação)          ← Hierarchical Compositional Coding
       ↓ texto TCF
   Arquivo TCF (LF only, sem brackets)
```

## Documentos

| Algoritmo | Camada | Codnome origem | Documento |
|---|---|---|---|
| **OBAT** — Online Bidirectional Affix Tokenizer | 1 (tokenização) | `alg16` | [OBAT.md](OBAT.md) |
| **HCC** — Hierarchical Compositional Coding | 2 (compactação) | `M8.A` | [HCC.md](HCC.md) |
| **TCF** — Tabular Compact Format | formato | (projeto) | [TCF-format.md](TCF-format.md) |

## Codnomes vs nomes oficiais

Os codnomes (`alg16`, `M8.A`) foram usados durante o desenvolvimento
experimental no dirty lab. Permanecem documentados em
`experiments/lab/dirty/notas/historia-dirty-lab.md` como identificadores
de **origem experimental**. Os nomes oficiais (OBAT, HCC) são usados
no código, docs públicas e referências externas.

## Veja também

- `../../experiments/lab/dirty/notas/historia-dirty-lab.md` —
  narrativa M0-M14 do desenvolvimento
- `../../experiments/lab/dirty/notas/roadmap-hipoteses.md` — direções
  futuras
- `../../src/tcf/` — implementação canônica
