# 2026-08-01-0141 — mapa de tipos internos: direção (preparação, SEM tipos novos)

One-shot de direção. O owner aprovou o **mapa de tipos internos visível e centralizado**:
`src/tcf/tipos_internos.py` (novo) é a fonte única das tabelas congeladas bool, declaradas
COMO DADOS — refactor byte-neutro do encoder/decoder (suíte 1087 passed, gates intactos,
wires byte-idênticos). O owner decide **depois** como o mapa será externalizado/configurável
(tem planos mais complexos); agora foi só preparação.

## Wire-sketches do owner (verbatim — REGISTRO, não implementado)

```
com true/false/null e afins
#TCF.8b264
FVRVUVVFVSqoqqKqiqoqqKqiqoqqKqiqog==

mas se for Masculino/Feminino onde 14 e 15 são tipos de conforto interno:
#TCF.8b264
\14
\15
FVRVUVVFVSqoqqKqiqoqqKqiqoqqKqiqog==
```

Leitura: o sketch estende o denso b2 com **domínio declarado no corpo** (`\14\n\15` antes do
payload) — o conforto viaja declarado uma vez, como o domínio do bN (ADR-0036) viaja, mas com
índices de conforto FIXOS (14/15) em vez de slots posicionais do domínio.

## Perguntas abertas — decisão do owner (T-TIPOS-CONFORTO-MAP)

1. **Mapa externo × config embutido versionado** — o mapa é contrato externo nas pontas
   (cf. direção 2026-07-16) ou config embutido versionado com o formato?
2. **Índices de conforto FIXOS de formato × alocados por schema** — 14/15 são congelados
   para sempre (como 0/1/2) ou cada schema aloca?
3. **Domínio declarado (`\14\n\15`) viaja sempre ou só fora da tabela implícita?** — no
   sketch ele viaja mesmo com índice fixo; é redundância inspecionável ou obrigação de
   decode?
4. **Conforto = tag nova (índice 6) × extensão da `b`** — o sketch usa `#TCF.8b2…` (extensão
   da família bool), mas masc/fem não é bool; a tag `b` aguenta o alargamento semântico?
5. **Quais tipos de formulário entram** — medir nos reais ANTES (SideOutputs/
   `column_features` já dão a porta: cardinalidade 2-3, domínio fechado recorrente).

## Fronteiras registradas (no docstring do módulo)

- `.8H` tem definition mask própria (`hierarchical.py`) — fora deste mapa.
- Slot 0 do `dominio_bn` (rota flat, ADR-0036) é convenção separada — mesmo valor, origem
  distinta; `tipos_internos.py` cobre a rota TIPADA.

## Regra até a decisão

**Nenhum tipo novo entra no `tipos_internos.py` sem o design do mapa.** 14/15 ficam como
EARMARK documentado — INATIVO. Tipo interno é contrato de formato: emitiu, congelou.
