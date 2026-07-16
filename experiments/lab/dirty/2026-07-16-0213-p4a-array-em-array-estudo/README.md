# Lab 2026-07-16-0213 — P4a: array-em-array via COUNT RECURSIVO

**Status**: estudo inspecionado e aprovado pelo owner → **WELDED** no core (`191babf`) → auditado.
**Fontes**: [p4-levantamento + revisão crítica](../notas/p4-replevel-nroots-levantamento.md) ·
[checkpoint 2026-07-16](../notas/checkpoints/2026-07-16-revisao-p2-p4.md) ·
[T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P4a) ·
[ADR-0033 §Update P4a](../../../../docs/adr/0033-hierarchical-codec-weld.md).

**Tese**: o repetition-level colapsa em **counts por nível** — elemento-de-array reusa o mecanismo
count→elementos recursivamente. A estrutura (contagens por nível) fica **legível sem materializar as
folhas** (princípio O(1)/stream/view do Ciclo 4).

> **Proveniência do gate**: o gate abaixo vem da seção *Revisão crítica independente* do levantamento,
> marcada lá como `[probatório→opinião; não é decisão do owner]`. Virou operativo por **adoção
> explícita do owner** ("pode abrir o lab P4a … o lab P4a que planejei com sua ajuda"). Não é, nem
> era, um parecer unilateral do owner — registrar isso importa para o P4b, onde **nada foi decidido**.

## Dois scripts, dois papéis

| script | quando | prova | saída |
|---|---|---|---|
| `study.py` + `proto.py` | **pré-weld** | a IDEIA (o protótipo extrai a ideia, não copia o core). Metas aqui são **pedagógicos**, sem sizes — **não são wire** | `outputs/00-estudo-proto.txt` |
| `run.py` | **pós-weld** | o **WIRE REAL** do core | `outputs/*.tcf` (24) + `outputs/*-rt.json` + `outputs/00-resultado.txt` |

> **Correção 2026-07-16** (achado do owner): o lab foi commitado **sem nenhum `.tcf`** — o protótipo
> nunca serializou wire, então a conclusão se apoiava em print. `run.py` fecha isso: cada caso do gate
> tem `.tcf` legível e roundtrip **byte-idêntico** ao canônico de `intermediates/` (`assert` + `diff`).

## A gramática (wire real, de `outputs/`)

Cada `#` abre um nível de array; `?` após o `#` = element-mask DAQUELE nível:

| construto | header real | arquivo |
|---|---|---|
| `[[1,2],[3]]` | `#TCF.8Hm#:3[#:8[]:8n` | `01-01-basico-1-2-3.tcf` |
| profundidade 3 | `#TCF.8Hcubo#:3[#:8[#:11[]:8n` | `01-03-profundidade-3.tcf` |
| array de arrays de objetos | `#TCF.8Hturmas#:3[#:8[nome` | `01-06-array-de-arrays-de-objetos.tcf` |
| **null ENTRE arrays** `[[1],null,[2]]` | `#TCF.8Hm#:3?:8[#:6[]:8n` | `01-07-null-entre-arrays-p3bp4a.tcf` |
| **null no inner** `[[1,null,2],[3]]` | `#TCF.8Hm#:3[#:8?:11[]:8n` | `01-08-null-dentro-do-inner-*.tcf` |
| **compose total** + typed | `#TCF.8Hm#:3?:8[#:8?:11[]:8n],rotulo:8,ok:5b` | `01-09-compose-total-p2-p3b-p4a.tcf` |

→ **null-entre-arrays = P3b∘P4a** (element-mask por nível): sem gramática nova, não é P5.

O wire de `[{"m":[[1,2],[3]]}]`, legível inteiro:

```
#TCF.8Hm#:3[#:8[]:8n
\2          <- 1 registro, 2 elementos no nível externo
*2-1|\2     <- counts internos: 2, 1   (seq-RLE)
*3+1|\1     <- folhas: 1, 2, 3
```

## Resultado — [outputs/00-resultado.txt](outputs/00-resultado.txt)

| etapa | resultado |
|---|---|
| **Didático** (12 formas = o gate) | **RT 12/12**, cada um com `.tcf` + roundtrip diffável |
| **Framing isolado** (carga constante, prof. 1→6) | **+7 B/nível, exato e constante** |
| **Árvore cheia** (prof. 1→5) | confundido de propósito (folhas dobram) — **não** ler como custo de nível |
| **Fuzz de profundidade** (seedado, níveis 1–4, ~20% null/nível, n/b/s) | **4000/4000** (`study.py`) |
| **Adversarial no wire real** (tag desconhecida, `]` deletado, bytes apendados, corpo esvaziado) | fail-loud 4/4 |

## Colunas

`(p,'count',0) [, (p,'emask',0)], (p,'count',1) [, (p,'emask',1)], …, folhas` — counts do nível k+1
têm 1 entrada por elemento NÃO-null do nível k (denso, consistente com P3b). No wire: nível 0 sem
sufixo (byte-compat com o pré-P4a), internos `count1`/`emask1`, …

## Fronteira

- **P5 union** (tipo misto no mesmo array) — fail-loud, fora daqui.
- **P4b raiz generalizada** — contrato público; **nada decidido** → [notas/p4b-levantamento.md](../notas/p4b-levantamento.md).
- Reuso entre níveis / "colunas com buracos" → `H-REPLEVEL-FLAT-VS-PORNIVEL-01` (`.9`).
