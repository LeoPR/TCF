# Research notes — workbench v0.6

> **Fonte da verdade atual**: dirty lab v0.6, sintetizado em
> [`historia-dirty-lab.md`](../../../experiments/lab/dirty/notas/historia-dirty-lab.md)
> (atualizada ate' M9, 2026-05-17).
>
> Esta pasta contem notas vivas do ciclo v0.6 (reset 2026-05-10).
> Tudo anterior esta em [`_archive/`](_archive/) como blueprint
> nao-canonico.

## Estado canonico (apos M9)

Componentes:

| Componente | Versao canonica | Localizacao |
|---|---|---|
| Algoritmo base | TCF-CORE (alg16) | `experiments/lab/dirty/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py` |
| Sintaxe ambiguidade local | M1.E | `experiments/lab/dirty/2026-05-12-M1-marcacao-ambiguidade/M1-E-range/` |
| Compactacao composicional | M8.A | `experiments/lab/dirty/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/` |

Compressao medida (dirty canonicos D1-D4):
- M1.E baseline: 660 bytes
- M8.A: 574 bytes (-13% reducao adicional)

Stress D1-D9: 1615 bytes / 2973 raw = 54.3% ratio.

## Notas vivas

| Data | Nota | Conteudo |
|------|------|----------|
| 2026-05-17 | [historia-dirty-lab](../../../experiments/lab/dirty/notas/historia-dirty-lab.md) | **Narrativa canonica M0-M9** (substitui a sintese 2026-05-11) |
| 2026-05-17 | [roadmap-hipoteses](../../../experiments/lab/dirty/notas/roadmap-hipoteses.md) | Hipoteses futuras (pre-tx, decomposicao, escala) |
| 2026-05-17 | [naming-compactacao-composicional](../../../experiments/lab/dirty/notas/naming-compactacao-composicional.md) | Terminologia oficial |
| 2026-05-16 | [convencao-output-tcf](../../../experiments/lab/dirty/notas/convencao-output-tcf.md) | Output: sem brackets, LF only |
| 2026-05-14 | [marcadores-multiplo-proposito](../../../experiments/lab/dirty/notas/marcadores-multiplo-proposito.md) | Operadores composicionais |
| 2026-05-14 | [comparacao-modular-camadas](../../../experiments/lab/dirty/notas/comparacao-modular-camadas.md) | Pre-tx layers |
| 2026-05-14 | [vetores-de-comparacao-alem-de-bytes](../../../experiments/lab/dirty/notas/vetores-de-comparacao-alem-de-bytes.md) | Velocidade/memoria/streaming |
| 2026-05-13 | [quebra-de-linha-como-marcador](../../../experiments/lab/dirty/notas/quebra-de-linha-como-marcador.md) | Quebra como marker |
| 2026-05-11 | [sintese-algoritmos-v06](2026-05-11-sintese-algoritmos-v06.md) | Sintese exps 01-15 — **HISTORICA, superada por historia-dirty-lab** |

## Sobre `_archive/`

Contem notas e consolidados das versoes anteriores (v0.0 a v0.5).
**Nao sao referencia canonica para v0.6.** Servem para:

- Localizar bugs e armadilhas ja' encontradas em ciclos anteriores
- Resgatar ideias antigas que podem ser **rebatizadas como
  hipoteses novas** e re-testadas no dirty v0.6 (nao importadas)
- Rastreabilidade historica

Nenhuma conclusao dos `_archive/` deve ser citada como evidencia
em ticket, finding ou paper sem ser re-validada pelo dirty v0.6.

## Para leitura rapida ("quem chegou agora")

1. Comecar pela
   [historia-dirty-lab](../../../experiments/lab/dirty/notas/historia-dirty-lab.md).
2. Depois ver o macro mais recente
   ([M9](../../../experiments/lab/dirty/2026-05-17-M9-stress-adversarial/README.md)
   ou
   [M8](../../../experiments/lab/dirty/2026-05-16-M8-virtual-refs-clean-output/README.md))
   para o estado tecnico atual.
3. Para direcoes futuras, ver
   [roadmap-hipoteses](../../../experiments/lab/dirty/notas/roadmap-hipoteses.md).
