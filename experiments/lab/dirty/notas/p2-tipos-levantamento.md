---
title: LEVANTAMENTO — P2 tipos (number/bool) no #TCF.8H — PARA INSPEÇÃO DO OWNER
type: plan
status: aberta
created: 2026-07-16
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/notas/tipos-como-specs.md (H-TYPE-01 C-híbrida)
  - experiments/lab/dirty/2026-07-06-2221-tcf8h-fidelidade-tipos/
  - experiments/lab/dirty/notas/substituicao-indices-especiais-plano.md (bool→índice, Ciclo 2)
---

# Levantamento — P2 tipos (o que vamos fazer). Para inspeção.

> **DECISÕES FECHADAS (owner 2026-07-16)**: as 5 recomendações abaixo APROVADAS. (1) tag de 1 letra;
> (2) UM tag `n` p/ number (json distingue int/float); (3) tag `b` p/ bool AGORA — e a **letra pode
> virar vantagem p/ marcar rápido como índice-interno depois** (a MEDIR sob [[H-PROFILE-01]], não
> bloqueia); (4) number+bool JUNTOS (P2); (5) number na forma `json.dumps` canônica. Regra extra
> (descoberta): **colunas TIPADAS sempre emitem `:size<tag>`** (só string-default pode omitir size na
> última folha) — resolve a ambiguidade `nomen` vs nome-tipo na última folha. Segue a implementação.

## O que é P2 (e o que NÃO é)

Preservar os **tipos escalares do JSON**: **number** (int/float) e **bool** (true/false). `null` já
está feito (P3, máscara). `string` é o default. **Fora**: `NaN`/`±Inf` (não são JSON RFC 8259);
tipo-misto num campo (número num registro, string em outro = **P5 union**, segue fail-loud).

## A lacuna (repro, medido 2026-07-16)

`encode_hierarchical` faz `str(v)` em toda folha escalar → coerção LOSSY:
`[{'idade':30,'ativo':True,'nota':9.5}]` → decode `[{'idade':'30','ativo':'True','nota':'9.5'}]`
(int/float/bool viram string; `'True'` nem é JSON). RT falha no TIPO.

## INSIGHT que SIMPLIFICA (corrige o medo do H-TYPE-01)

O H-TYPE-01 temia deduzir tipo de STRINGS ambíguas (`007`, `1e3`, `12.30`). **Mas o codec recebe
OBJETOS PYTHON, não texto** — o tipo é **CONHECIDO no encode** (`isinstance`), não deduzido. Então:
- não há "007 é int ou string?" — se veio Python `int`, é number; se veio `str "007"`, é string.
- não há problema de canonicalização de texto: `repr`/`json.dumps` de float **faz round-trip exato**
  em Python (`float(repr(x))==x`); int idem. Medido: `0`,`30`,`-5`,`1.0`,`0.1`,`-0.0`,big-int RT-safe.

→ P2 vira **tag por-COLUNA** (não dedução por-valor de string). Limpo e RT-exato p/ coluna
consistentemente-tipada. A dedução-por-valor do H-TYPE-01 só é necessária no caso MISTO (P5).

## Mecanismo proposto (por-coluna; a máscara/def-level já resolve null ortogonalmente)

| tipo da coluna (dos valores Python) | armazena | decode | tag |
|---|---|---|---|
| **string** (default) | o valor | identidade | — (sem tag) |
| **number** (int E/OU float, exceto bool) | `json.dumps(v)` (`30`, `9.5`, `1000.0`) | `json.loads` | 1 letra |
| **bool** (só `True`/`False`) | `true`/`false` | `json.loads` | 1 letra |

- **number** com `json.dumps`/`json.loads` preserva **int vs float por valor** (o `.` no texto
  distingue) → uma coluna `[1, 1.5, 2]` (int+float misto, ambos JSON-number) faz RT sem tag por-valor.
- **bool**: JSON bool é SÓ `true`/`false`. `1/0`, `t/f`, `Y/N`, `sim/não` são STRINGS (variante — fora
  do P2; viram string). A capacidade "variante" (mesma spec bool com superfícies diferentes) fica p/
  depois (natures/índice-interno).
- **compõe com P3**: campo/elemento nullable-tipado → máscara `0` p/ null + tag da coluna p/ os
  não-nulos. Ortogonal (validity ⊥ tipo — como Arrow/Parquet).

## DECISÕES a fechar (o que peço que você inspecione)

1. **Gramática do tag** — onde e quais letras. Candidato (H-TYPE-01): 1 letra **colada no size**
   (`idade:4i`, `nota:6f`, `ativo:5b`). PRECISA compor com máscara e element-mask:
   `campo?:msize:size<tag>` (campo nullable tipado) e `arr#:csize?:emsize[]:asize<tag>` (elemento
   tipado). Verificar ambiguidade no parser (o tag é 1 letra após o size do dado).
2. **number: um tag só ou int/float separados?** Proposta: **UM tag `number`** (json.dumps/loads
   distingue int/float pelo `.`) — mais simples, cobre misto. Alternativa: tags `i`/`f` separados
   (o H-TYPE-01) — só útil se quisermos proibir misto int/float (não recomendo; JSON permite).
3. **bool: tag agora, índice-interno depois?** Decisão Ciclo-4: máscara/tag é o canônico; o
   índice-de-substituição (bool via dicionário-interno da versão) é NICHO de perfil. Proposta: **tag
   `b` agora** (true/false no corpo); índice-interno = otimização `.9`/perfil (H-PROFILE-01), não bloqueia.
4. **Escopo: P2 = number+bool juntos, ou P2a number → P2b bool?** Proposta: **juntos** (mesma
   mudança: sub-tipo do escalar + tag no meta + json no corpo); são pequenos e simétricos.
5. **Autoridade/canonicalização**: declarar que number é armazenado na forma `json.dumps` (canônica).
   Um float `9.50` já é `9.5` em Python — não há "9.50" a preservar (isso é texto, não valor).

## Fronteira / fora (declarar)

- **NaN/±Inf**: fora (não-JSON). Se aparecerem no Python, decidir: fail-loud (recomendo) ou natures.
- **tipo-misto** num campo (int+string, number+object): **P5 union**, segue fail-loud (auditoria).
- **variantes de bool** não-JSON (1/0, sim/não): são string no P2; spec-bool-variante = futuro.
- **int gigante / precisão**: Python int arbitrário + float repr-exato → RT-safe (medido).

## Metodologia (padrão P1/P3)

Estudo-primeiro (didático: cada tipo + os edge de RT-safety + composição com null; realista; massa)
→ fechar a gramática do tag → weld no core (aditivo em L2; escalar ganha sub-tipo) → gate
byte-canônico + **auditoria adversarial** (a lição: gramática nova esconde corrupção). Uniforme
all-string continua byte-idêntico (tag só aparece em coluna tipada).

## Confiança

`Média-Alta` no design (o insight Python-tipado remove a parte difícil). O que falta é fechar as 5
decisões acima e provar RT nos edge (float precision, misto int/float, big-int, bool, null+tipo juntos).
