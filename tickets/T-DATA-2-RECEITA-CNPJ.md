---
title: T-DATA-2-RECEITA-CNPJ — Dataset real de CNPJ (Receita Federal open data) para gating ecologico das natures
status: in-progress
priority: P2
created: 2026-06-01
updated: 2026-06-02
blocked-by: []
related:
  - datasets/canonical/br-identidades/   (contraparte SINTETICA; este fecha o gate que aquele nao pode)
  - docs/adr/0015-natures-templated-checked-weld.md
  - src/tcf/natures/templated_checked.py  (SPEC_CNPJ — alvo)
  - tickets/T-DATA-1-datasets-financeiros-cientificos.md  (padrao setup canonical)
---

# T-DATA-2-RECEITA-CNPJ — CNPJ real para gating ecologico

## Contexto / motivacao

As natures CPF/CNPJ (ADR-0015, welded em `src/tcf/natures/`) **nao tem
dataset canonico real**. O `br-identidades` (sintetico, criado 2026-06-01)
valida round-trip lossless + gate de ativacao `n_compressible>=~50%`, mas
pela regra anti-incidente (CLAUDE.md L108-128, Brunswik 1956) **dado
sintetico NAO pode sustentar `confirmada-empirica`** — e' "construido pra
testar a hipotese".

Achado-chave da revisao de design (workflow 2026-06-01): **dados publicos de
CNPJ da Receita Federal sao nao-PII** (pessoa juridica), com digito
verificador mod-11 real. E' o unico caminho identificado que pode levar a
nature CNPJ a `confirmada-empirica` com dado ecologico.

> CPF real e' PII e NAO pode ser commitado/sourced — pra CPF, sintetico-com-
> digito-valido e' o teto etico. So' a nature **CNPJ** tem caminho real.

## Hipotese / pergunta

**H-NAT-CNPJ-RW**: a nature CNPJ (SPEC_CNPJ, mod-11 elision -> base94)
mostra ganho >= 5% weighted em coluna de CNPJ de dataset REAL (Receita),
similar ao observado em sintetico (lab 54-61% isolado), confirmando
generalizacao?

## Plano

1. **ANTES de propor download** — rodar checklist discoverability (CLAUDE.md):
   `Glob scripts/setup_*.py`, checar `Z:/tcf-data/external/` por slice ja'
   baixado, confirmar que nao existe outro dataset CNPJ no repo.
2. **Fonte**: Receita Federal Dados Publicos CNPJ
   (https://dadosabertos.rfb.gov.br/CNPJ/). Base completa ~60M
   estabelecimentos (varios GB). **NAO baixar tudo** — pegar 1 arquivo de
   estabelecimentos e amostrar slice de 200k-600k linhas.
3. **Colunas alvo**: cnpj_basico+ordem+dv (montar CNPJ formatado
   NN.NNN.NNN/NNNN-DD), razao_social/nome_fantasia (free text real),
   municipio (codigo), cnae (codigo), situacao_cadastral (low-card).
4. **setup_receita_cnpj.py** seguindo padrao `setup_*.py`: download (ou
   apontar pra arquivo local), parse, monta CNPJ formatado, escreve CSV em
   `Z:/external/`, metadata + README leve em git, sample 100 linhas, e
   **fixture frozen de 2000 CNPJs** em `datasets/samples/` pro gate
   real-world (analogo a test_real_world_snapshots.py — hoje nao existe
   fixture BR de check-digit).
5. **csv_to_sqlite** -> hub. Validar % de CNPJs que classificam
   `compressible` sob SPEC_CNPJ (real pode ter formatos sujos -> fallback).
6. **Medir** nature ON vs OFF na coluna CNPJ real; reportar bytes absolutos
   + weighted. Comparar sintetico (br-identidades) vs real (synthetic-vs-real
   da checklist Q3).

## Criterio de aceite

- [ ] Checklist discoverability rodado + aprovacao explicita do owner pro
      download (anti-incidente EXP-012)
- [ ] `scripts/setup_receita_cnpj.py` + metadata + README (referencia leve)
- [ ] Fixture frozen 2000 CNPJs reais em `datasets/samples/receita-cnpj/`
- [ ] % compressible medido na coluna real; fallback caracterizado
- [ ] Ganho weighted CNPJ real medido e comparado ao sintetico
      (>= 5% -> candidato a `confirmada-empirica`; < 5% -> documentar)

## Riscos

1. **Download grande** (GB). Mitigar: 1 arquivo + slice, nunca base completa.
2. **Formato sujo real** (CNPJ sem mascara, com espaços) -> muito fallback;
   pode mascarar o ganho. Caracterizar antes de concluir.
3. **N>=5 fontes / N>=20**: 1 dataset CNPJ real nao basta sozinho pro gate
   estatistico forte — registrar como 1a fonte ecologica de check-digit.
4. **Licenca/uso**: dados abertos Receita, mas confirmar termos antes de
   redistribuir qualquer fixture.

## Conexoes

- Contraparte sintetica: `datasets/canonical/br-identidades/` (valida RT +
  gate; este valida generalizacao)
- ADR-0015 (natures welded); META-TYPE-ENCODERS (nature 4 "Checked")
- Padrao setup: T-DATA-1

## Updates datados

### 2026-06-02 — script criado + logica provada; download bloqueado por rede

Checklist discoverability OK (nenhum dado CNPJ em repo nem em Z:). Layout
confirmado de fonte oficial (okfn-brasil/receita startdb.sql): arquivo
**Estabelecimentos** = 30 colunas, `;`-separado, **sem header**, encoding
**ISO-8859-1 (Latin-1)**, em 10 partes (Estabelecimentos0..9.zip, ~290MB
cada). CNPJ vem partido em 3 colunas: cnpj_basico(8) + cnpj_ordem(4) +
cnpj_dv(2) -> montar `NN.NNN.NNN/NNNN-DD`.

**`scripts/setup_receita_cnpj.py` criado** (download 1 parte -> unzip ->
slice N linhas -> monta+valida CNPJ contra SPEC_CNPJ -> projeta 8 colunas
-> hub + fixture 2k). **Logica de parse/montagem/validacao PROVADA** contra
um zip sintetico no formato real (30 col, `;`, latin-1): 95% compressible
com 5% dv-ruim plantado, round-trip OK. `--zip <path>` processa um arquivo
ja' baixado (sem rede).

**BLOQUEIO de rede (deste ambiente)**: host oficial
`dadosabertos.rfb.gov.br` da' **timeout** (WinError 10060); mirror
`arquivos.receitafederal.gov.br` responde no root (200, portal SERPRO JS)
mas 404 em todo path `/dados/cnpj/...` documentado; dados.gov.br API = 401
(precisa token); Casa dos Dados = so' landing page. Logo o download real
**nao roda deste sandbox** — mas a fonte e' BR e provavelmente alcancavel
da rede do owner.

**Como completar (owner, na rede dele)**:
```bash
# opcao A — autodetect + download:
python scripts/setup_receita_cnpj.py --rows 200000
# opcao B — se autodetect falhar, fixar periodo:
python scripts/setup_receita_cnpj.py --period 2025-05 --rows 200000
# opcao C — baixar 1 zip manual e processar offline:
python scripts/setup_receita_cnpj.py --zip Z:/tcf-data/external/receita-cnpj/Estabelecimentos0.zip --rows 200000
# depois:
python scripts/csv_to_sqlite.py receita-cnpj
```
Apos rodar: medir % compressible na coluna `cnpj` real + ganho nature ON/OFF
(weighted) e comparar com o sintetico br-identidades (checklist Q3).
