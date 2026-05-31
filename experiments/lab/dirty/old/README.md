# dirty/old/ — historia v0.6 inicial (M0-M14)

**Movido pra ca em 2026-05-16** durante reorganizacao do dirty lab.
Pastas preservadas com history git (`git mv`).

> **Importancia historica**: este e' o **dirty lab onde o canonical
> TCF-CORE foi desenvolvido**. Codigo welded pra `src/tcf/` saiu
> daqui (M11-M13). M9 stress validou D1-D9 (1615 bytes total,
> ratio medio 54.2%). M14 e' o ultimo baseline byte-canonical.

## Convencao de naming (com erros preservados)

Pastas datadas `YYYY-MM-DD-M<N>-<descritor>/`. As datas:
- Algumas REAIS (M0, M1, M2 datadas com ~uma data realista)
- M9-M14 com dates `2026-05-17-*` que **eram impossiveis** quando
  criadas (futuras). Erro antigo: data foi tratada como incremento
  de macro em vez de data real. Preservado pra rastreabilidade git.

## Estado das macros (era / foi)

> `era` = pre-reset (Mobsolete) — NAO canonico
> `foi` = fechado, contribuiu pra canonical atual

| Pasta | Estado | Foco | Contribuicao canonical |
|---|---|---|---|
| `Mobsolete/` | era | blueprints pre-reset (26 exps 2026-05-07..25) | NAO canonico |
| `M0-fase-exploratoria-inicial/` | foi | 16 exps -> algoritmo raiz | `online.py` = **OBAT (alg16)** atual em src/tcf/core/ |
| `M0.5-exploracao-sintaxe-pre-M1/` | foi | 12 variantes de sintaxe | Interface `Syntax` |
| `2026-05-12-M1-marcacao-ambiguidade/` | foi | marcacao ambiguidade local | M1.E base (-10.6% vs M1.A); regra de ouro |
| `2026-05-13-M2-redundancia-entre-linhas/` | foi | tupla aliases | M2.A subsumido em M5 |
| `2026-05-13-M3-encadeamento-declaracoes/` | foi | encadeamento | dim mapeada, net 0 |
| `2026-05-13-M4-desfragmentacao-arvore/` | foi | desfragmentacao | M4.C1' superado por M6.C |
| `2026-05-14-M5-pilha-M2A-M4C1p/` | foi | pilha (revisada em M6) | — |
| `2026-05-14-M6-sintaxe-composicional/` | foi | `~` cria ref auto-nomeado | M6.C (-8.4% vs M1.E) |
| `2026-05-15-M7-refactor/` | foi | refactor + debug | mesma bytes, codigo melhor |
| `2026-05-16-M8-virtual-refs-clean-output/` | foi | detector unificado | **M8.A 574 bytes** = **HCC** atual em src/tcf/composicional/ |
| `2026-05-17-M9-stress-adversarial/` | foi | 9 datasets sinteticos | RT 9/9 OK; ratio medio 54.2%; 1615 bytes |
| `2026-05-17-M10-datasets-elevation/` | foi | smoke test datasets canonicos | byte-identico a M9 |
| `2026-05-17-M11-welding-step1-alg16-src/` | foi | welding alg16 pra src/tcf/core/ | byte-identico a M10 |
| `2026-05-17-M12-welding-step2-m8a-src/` | foi | welding M8.A pra src/tcf/composicional/ | byte-identico a M11 |
| `2026-05-17-M13-welding-step3-api-publica/` | foi | API publica `from tcf import encode, decode` | byte-identico a M12 |
| `2026-05-17-M14-clean-validation-srctcf/` | foi | re-roda M13 pos-cleanup | **byte-identico a M13**; baseline final |

## Importancia pra desenvolvimento atual

- **M14** e' o **baseline byte-canonical** referenciado em
  [`../../clean/EXP-007-prototipo-tcf-core/config.json`](../../clean/EXP-007-prototipo-tcf-core/config.json).
- **Codigo welded** em `src/tcf/` tem referencias historicas a
  pastas aqui em docstrings (preservado).
- **D1-D9** datasets canonicos elevados de M9 estao em
  [`../../../../datasets/synthetic/`](../../../../datasets/synthetic/).

## Narrativa completa

Ver [`../notas/historia-dirty-lab.md`](../notas/historia-dirty-lab.md)
pra cronologia M0-M14 com decisoes e learnings.
