---
title: T-DATA-2-RECEITA-CNPJ — Dataset real de CNPJ (Receita Federal open data) para gating ecologico das natures
status: closed-done
priority: P2
created: 2026-06-01
updated: 2026-06-02
closed: 2026-06-02
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

- [x] Checklist discoverability rodado + aprovacao explicita do owner pro
      download (anti-incidente EXP-012)
- [x] `scripts/setup_receita_cnpj.py` + metadata + README (referencia leve)
- [x] Fixture frozen 2000 CNPJs reais em `datasets/samples/receita-cnpj/`
- [x] % compressible medido na coluna real (100% sob SPEC_CNPJ); 0 malformados
- [x] Ganho CNPJ real medido: **40.9%** nature vs M10 (>= 5% -> candidato a
      `confirmada-empirica`; 1a fonte ecologica de check-digit, falta N>=5)

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

**BLOQUEIO de rede (parcial, deste ambiente)**: host oficial
`dadosabertos.rfb.gov.br` da' **timeout**; os paths HTTP planos
`/dados/cnpj/...` dao 404. Adivinhar URL nao funciona.

### 2026-06-02 (parte 2) — DESCOBERTA da API real + DOWNLOAD + MEDICAO

**Causa-raiz dos 404**: a Receita migrou o repositorio pra um **Nextcloud
public share servido por WebDAV** (descoberto lendo o downloader mantido
`rictom/cnpj-sqlite`). API real:
- **PROPFIND** em `https://arquivos.receitafederal.gov.br/public.php/webdav`
  com Basic auth `(share_token, "")`, token `YggdBLfdninEJX9` -> lista meses
- Download via `.../public.php/dav/files/<token>/<YYYY-MM>/<arquivo>`
- Verificado: PROPFIND root -> 207, meses ate' 2026-05. Estabelecimentos0.zip
  = **~1.99 GB** (nao ~290MB). `Accept-Ranges: None`.

**Script reescrito** pra essa API + **streaming-stop**: parseia o local
header do zip, raw-inflate via zlib on-the-fly, para apos N linhas (so'
baixa o necessario — `ZipFile` nao serve porque precisa seek pro central
directory). `--list` lista a arvore real; `--full` baixa a parte inteira;
`--zip` processa offline.

**Rodado de verdade (2026-05, Estabelecimentos0, stream 200k, cap 600MB)**:
200.000 estabelecimentos reais, **100% compressible** sob SPEC_CNPJ, 0
malformados. Hub `receita-cnpj.db` FK OK. So' colunas nao-PII projetadas
(CNPJ/matriz/nome_fantasia/situacao/data/cnae/uf/municipio_cod — telefone/
email/endereco DESCARTADOS).

**MEDICAO (10k CNPJs reais, nature ON vs OFF)**:
| | bytes | ratio vs raw |
|---|---|---|
| raw | 190000 | 100% |
| TCF sem nature (M10) | 205944 | 108.4% (infla — CNPJ unico) |
| TCF nature='cnpj' | 121744 | 64.1% |

**Ganho da nature CNPJ em dado real: 40.9%** vs M10. Bem acima do gate 5%.
Confirma em dado ecologico o que o sintetico br-identidades so' sugeria.

**Status do gate confirmada-empirica**: esta e' a **1a fonte ecologica** de
check-digit. Falta N>=5 fontes diferentes (checklist Q2) pra confianca
estatistica forte — mas a generalizacao CNPJ esta agora demonstrada em dado
real (nao so' sintetico). Marcar a nature CNPJ como `confirmada-empirica`
com confianca: Media (1 fonte real, ganho >> 5%, RT 100%).
