# Naming — "Compactacao composicional"

**Data**: 2026-05-17
**Tipo**: nota terminologica
**Origem**: user pediu nome melhor para a etapa que era chamada
"desfragmentacao da arvore" (em M4) e "sintaxe composicional" (em M6+).

## Contexto

O TCF tem 2 etapas conceituais:

1. **TCF-CORE / OAS / alg16**: tokenizacao incremental.
   Produz tokens raiz por string (TokLit, TokRefPref, TokRefSuf).
   Estabelecido em M0.

2. **(esta etapa)**: pega os tokens raiz + atomos provisionais e
   produz BODY textual compacto. Inclui:
   - Atomos como refs (M1.E style com range)
   - Composicoes via `~` (cria refs auto-nomeados)
   - Reuso via bare ref id
   - Detector que encontra sub-tuplas reusaveis

Nome atual da etapa: variavel ao longo do tempo:
- M4: "desfragmentacao da arvore" (foco no rearranjo)
- M6: "sintaxe composicional" (foco no operador `~`)
- M8: detector "unificado" (foco no algoritmo de busca)

## Proposta de nome

**Compactacao composicional**

Justificativa:
- "Compactacao": reflete o objetivo (reducao de bytes).
- "Composicional": reflete o mecanismo (composicoes via `~`).
- Concisa e nao ambigua. Nao confunde com TCF-CORE.

## Alternativas consideradas

| Nome | Pros | Contras |
|---|---|---|
| **Compactacao composicional** | Captura objetivo + mecanismo | Verboso |
| Compressao composicional | Idem mas "compressao" e' ambigua | Confunde com gzip |
| Composicao de nos | Foco no mecanismo | Nao captura objetivo |
| Minimizacao de refs | Foco no resultado | Tecnico demais |
| Optimizacao do body | Generico | Vago |
| Desfragmentacao | Termo antigo (M4) | Implica rearranjo, mais que compacao |
| Detector de composicoes | Foco no algoritmo | So' um aspecto |

## Adopcao

**Termo canonico em docs futuros**: **Compactacao composicional**.

Quando precisar diferenciar:
- "Compactacao composicional" = a etapa toda (detector + emit).
- "Detector de composicoes" = especificamente o algoritmo de busca
  de sub-tuplas.
- "Emit composicional" = especificamente a serializacao com `~`/`,`.

## Estrutura TCF (apos M9)

```
[Pre-tx camada opcional]
  ↓
TCF-CORE / OAS / alg16
  ↓ (tokens raiz por string)
Compactacao composicional (M8.A)
  ↓ (body textual compacto)
[Cleanup + header]
  ↓
Arquivo TCF final
```

## Conexoes

- [[historia-dirty-lab.md]] — narrativa completa
- [[../../2026-05-16-M8-virtual-refs-clean-output/]] — implementacao canonica
- [[convencao-output-tcf.md]] — convencao do body emit
