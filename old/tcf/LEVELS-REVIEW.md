---
title: LEVELS-REVIEW — revisão dos níveis L0–L3 do motor antigo (v0.2/v0.5)
type: reference
status: archived-reviewed
created: 2026-06-02
audience: ai-primary, human-secondary
reviewer-principle: a fonte autoritativa é o CÓDIGO (old/tcf/encoder.py), não a prosa antiga
applies-to: old/tcf/ (motor columnar pré-v0.6, NÃO confundir com src/tcf/ canonical)
---

# Revisão dos níveis L0–L3 (motor antigo `old/tcf/`)

> **Chesterton's fence**: este doc registra *por que* os níveis L1/L2/L3
> existiam e *o que* significavam, ANTES de qualquer decisão de absorver/
> apagar. O motor `old/tcf/` está **congelado-histórico** — `src/tcf/`
> (canonical v0.6) tem **acoplamento zero** com ele (verificado:
> `git grep old.tcf -- src/` → nada). Nenhuma modificação foi feita ao
> motor; isto é entendimento read-only.

## Contexto

`old/tcf/` é o motor **columnar-para-LLM** do ciclo v0.2→v0.5 (header
emitido: `# TCF v0.2`; `__version__ = "0.2.0"`). Ele foi **substituído**
pelo pipeline canonical v0.6 em `src/tcf/` (OBAT + HCC, formato `#TCF.6`
congelado por ADR-0017). Os "níveis" (`EncodeConfig.level`) são o conceito
de compressão progressiva desse motor antigo — **não existem no v0.6**
(que usa pipeline delta-aware em camadas, sem `level=N`).

## (1) Semântica AUTORITATIVA dos níveis — derivada do código

Fonte: [`old/tcf/encoder.py`](encoder.py) (`encode_columns`, linhas 169–221)
+ [`old/tcf/__init__.py`](__init__.py) docstring + `EncodeConfig` (linha 50).

| Nível | O que faz (código) | Reversível? | Referência no código |
|-------|--------------------|-------------|----------------------|
| **L0** | Expanded — um valor por linha, sem compressão | ✅ exato | `level >= 1` falso → `lines.extend(vals)` (enc:219-220) |
| **L1** | RLE nas colunas (`N*val` = val repetido N vezes) | ✅ exato | `rle_encode(vals)` (enc:216-218); header `# N*val` (enc:189) |
| **L2** | Sort pela coluna de menor cardinalidade + RLE (**default**) | ✅ exato | `sort_columns(cols)` (enc:171-172); `EncodeConfig.level=2` default (enc:50) |
| **L3** | Dicionário (texto→índices) **+ sort + RLE** | ✅ exato | `dict_build` por coluna de texto (enc:176-181); emite `# dict col: ...` (enc:200) |

Flags **ortogonais** ao nível:
- **`include_stats`** (default True): emite `# STATS col: n=.. sum=.. min=.. max=.. avg=..`
  por coluna numérica; com `full_n` > n, anexa intervalo de confiança
  (`err=X% full_n=N`). Código: `_stats_line` (enc:62-107).
- **`precision`**: casas decimais no formato numérico (`fmt_num`).

## (2) CONTRADIÇÃO a registrar (era exatamente o motivo de "rever")

A documentação antiga **diverge do código** na ordem dos níveis:

| Fonte | L1 | L2 | L3 | Confere com código? |
|-------|----|----|----|---------------------|
| **`old/tcf/encoder.py`** (CÓDIGO, autoritativo) | RLE | sort+RLE | dict+sort+RLE | — (é a fonte) |
| `docs/archive/manual_v05/03-compression-levels.md` | +DICT | +RLE | schema-only | ❌ ordem trocada + L3 errado |
| `docs/archive/article_v05/03-tcf-format.md` | RLE | sort+RLE | dict+sort+RLE | ✅ consistente com código |

→ **O código é autoritativo.** O `manual_v05/03-compression-levels.md`
está **errado** na ordem (diz L1=DICT/L2=RLE; código é L1=RLE/L2=sort+RLE)
**e** na definição de L3. O `article_v05/03-tcf-format.md` está correto —
citar este como a prosa consistente.

## (3) "L3 = schema-only" é ficção neste motor

O manual_v05, o README antigo (seção v0.5) e tabelas de tokens descrevem
um **L3 "schema-only"** (descarta todas as linhas, emite só schema+STATS,
~0.05–0.10× CSV, **não** round-trip). **Isso NÃO está implementado em
`old/tcf/encoder.py`**: L3 ali ainda emite todas as linhas como índices de
dicionário (round-trip exato). "schema-only" era um **conceito da Linha B**
(LLM gera SQL a partir do schema) — um artefato de doc/benchmark, não um
modo do encoder.

**Pendência para o reviewer** (não bloqueante): confirmar se "schema-only"
chegou a existir em `old/tcf/v05/` (o segundo motor SRDM, ver §extra) ou
em algum runner de `experiments/eval/`, ou se foi **sempre** só prosa.
Até confirmar: tratar como **não implementado no motor de níveis**.

## (4) Linhas do README de-staladas nesta passada

As referências v0.5 no `README.md` que implicavam que os níveis são atuais
foram corrigidas/cercadas como histórico v0.5 (ver commit desta reorg):
quickstart `encode_rows`/`EncodeConfig(level=2)` + `python -m tcf encode
--level 2` (quebrado contra `src/tcf/`), tabela "TCF L2/L3", menção a
`include_stats=True`. Decisão aplicada: **cercar como `(v0.5 histórico)`**
apontando para este review + `docs/archive/manual_v05/`, mantendo o
quickstart v0.6 (`from tcf import encode, decode`) como o corrente.

## Extra — dois motores dentro de `old/tcf/`

`old/tcf/` contém DOIS motores:
1. O motor de **níveis** (`EncodeConfig.level` inteiro) — descrito acima.
2. [`old/tcf/v05/`](v05/) — um motor **posterior** (SRDM via Flags, não a
   API de `level` inteiro).

**Pendência para o reviewer**: registrar se `v05/` **substitui** ou
**coexiste** com o motor de níveis, e **de qual motor** vieram os números
headline do benchmark v0.5 (ex: "7188 bytes / 86.9%"). Não resolvido nesta
passada (exige ler `v05/` + cruzar com `experiments/results/`); marcado
aqui para não se perder.

## Decisão de retenção

- **`old/tcf/` permanece em `old/`** (congelado-histórico; já excluído do
  wheel/sdist por `pyproject.toml`). NÃO mover, NÃO modificar.
- **Absorver-e-apagar depois**: seguro fazê-lo *após* este review +
  (opcional) um ADR retroativo registrando "por que L1/L2/L3 → OBAT/HCC".
  Este doc é o registro que torna a remoção futura rastreável (Chesterton's
  fence satisfeito).

## Conexões

- Motor canonical atual: [`src/tcf/`](../../src/tcf/) (OBAT+HCC, `#TCF.6`)
- Prosa v0.5 consistente: `docs/archive/article_v05/03-tcf-format.md`
- Prosa v0.5 **divergente** (a corrigir/avisar): `docs/archive/manual_v05/03-compression-levels.md`
- Decisão de congelar v1.0 sem CLI: `pyproject.toml` + ADR-0017
