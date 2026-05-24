---
title: Naturezas templated / checksummed (registro 2026-05-24)
type: brainstorm-conceitual
status: rascunho
tags: [theory, naturezas, templated, checksummed, lossy, futuro]
created: 2026-05-24
related:
  - docs/theory/data-natures-taxonomy.md
  - experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md
  - tickets/META-TYPE-ENCODERS.md
  - tickets/T-CODE-SCHEMA-BUILDER.md
---

# Naturezas templated / checksummed — registro

> Brainstorm 2026-05-24 apos owner mencionar exemplos especificos
> (CPF, IP, telefone, etc.) que merecem catalogacao separada.
> Estende `naturezas-numericas-2026-05-23.md` com **naturezas estruturais
> de strings formatadas** (templated) e **checksummed** (com digito
> verificador), alem de **lossy distribuido**.
>
> NAO implementar agora — registro pra reabertura futura quando
> META-TYPE-ENCODERS T02 (Templated) e T04 (Checked) saírem de
> "adiado" pra "ativo".

## Contexto

META-TYPE-ENCODERS ja' catalogou 8 naturezas (T01-T07 + High-entropy)
em 2026-05-15 com exemplos genericos. Owner pediu agora **detalhamento
por instancia comum** (CPF, IP, telefone, MAC, etc.) pra registro,
porque muitas tem **comportamento composto**: sao templated +
checksummed simultaneamente, ou templated + composite.

## Catalogacao por instancia

### Templated puro (layout fixo, sem checksum)

| ID | Tipo | Estrutura | Exemplo | Compressao alvo |
|---|---|---|---|---|
| TM-IP4 | **IPv4** | `N.N.N.N` (4 octetos, `.` separator) | `192.168.1.1` | Omitir `.` (3B → 0B); slots inteiros 0-255 cabem em 1B cada (4B vs 15B raw = -73%) |
| TM-IP6 | **IPv6** | `H:H:H:H:H:H:H:H` (8 grupos hex, `:` separator, `::` shorthand) | `2001:db8::1` | Omitir `:`; expandir `::` no encode; slots hex de 0-FFFF |
| TM-MAC | **MAC address** | `HH:HH:HH:HH:HH:HH` (6 bytes hex) | `00:1A:2B:3C:4D:5E` | Omitir `:`; cada slot = 1 byte (6B vs 17B raw = -65%) |
| TM-CEP | **CEP BR** | `NNNNN-NNN` (8 digitos, `-` separator) | `01310-100` | Omitir `-`; numerico inteiro (8 digit + delta-aware se sequencial) |
| TM-EAN | **EAN/UPC** | NNNNNNNNNNNNN (13 digits, no separator) | `7891234567890` | Puro numerico delta-aware |

### Templated com pontuacao opcional (multipla representacao)

| ID | Tipo | Forma comum | Forma "limpa" | Estrategia |
|---|---|---|---|---|
| TM-FONE-BR | **Telefone BR** | `(11) 99999-1234` ou `+55 11 99999-1234` | `11999991234` | Detectar mascara, extrair so digitos, encoder normaliza mascara no decode |
| TM-FONE-INTL | **Telefone E.164** | `+CC AAAA NNNNNNNN` | `CCAAAANNNNNNNN` | Composite: country code (enum) + numero local (templated) |
| TM-DATA-BR | **Data BR** | `dd/mm/yyyy` ou `dd-mm-yyyy` | `yyyy-mm-dd` ISO | Templated + composite + (frequente) incremental |
| TM-EMAIL | **Email** | `user@dominio.tld` | (sem normalizacao trivial) | Templated: 3 slots (user, dominio, tld) — OBAT ja' captura sufixo `@dominio.tld` parcialmente |
| TM-URL | **URL** | `scheme://host/path?query` | (sem normalizacao trivial) | Templated + hierarchical (path) — OBAT ja' captura prefixo `https://api.x.com/` |

### Templated + checksummed (dual nature)

Naturezas onde **parte do valor e' computavel** (dígito verificador):

| ID | Tipo | Estrutura | Check | Estrategia |
|---|---|---|---|---|
| TM-CPF | **CPF BR** | `NNN.NNN.NNN-DD` (11 digitos + 2 check) | `D1 = f(d1..d9)`, `D2 = f(d1..d9, D1)` | (a) Omitir `.` e `-`; (b) Omitir DD (regenera no decode); savings = 4 chars + 2 chars = -27% raw |
| TM-CNPJ | **CNPJ BR** | `NN.NNN.NNN/NNNN-DD` (12 digitos + 2 check) | `D1, D2` calculaveis | Similar CPF: omitir `.`/`/`/`-` + DD; savings ~28% raw |
| TM-TITULO | **Titulo de eleitor BR** | `NNNNNNNNNNNN` (10 digitos + 2 check) | check digit | Similar a CPF |
| TM-IBAN | **IBAN** | `CC NN BBBB BBBB ... CCCC` (15-34 chars) | mod-97 check | Omitir espacos + check (-15%) |
| TM-LUHN | **Cartao credito / IMEI** | NNNN NNNN NNNN NNNN (16 digits) | Luhn check digit final | Omitir espacos + ultimo digito (Luhn check) |

### Lossy com erro controlado

Naturezas onde **perda controlada** vale a pena. Estende #10 de
`naturezas-numericas-2026-05-23.md`.

| ID | Tipo | Descricao | Erro tolerado | Estrategia |
|---|---|---|---|---|
| LR-FLOAT-PREC | **Float com precisao fixa** | `3.14159` truncado pra `3.14` | erro absoluto |delta| < eps | Encoder: round(val, precision); precisao no header |
| LR-GEO | **Coordenadas geo** | `-23.550520, -46.633308` truncado pra `-23.55, -46.63` | erro espacial ~1km vs ~100m | Round lat/long pra N casas; reverse: range relevante |
| LR-MONETARY | **Monetario com round** | `R$ 12.345,678` → `R$ 12.345,68` | erro <= 0.01 | Round pra 2 casas (centavo) — padrao financeiro |
| LR-DIST | **Erro distribuido** | Sensor com noise gaussian | erro RMS < threshold | Quantize + delta-encode quantized values; perda controlada |
| LR-PERC | **Percentual aproximado** | `45.67%` -> `45.7%` ou `46%` | erro % | Round pra N casas; tabular reports tipicamente OK |

### Composite (multi-nature por valor)

Naturezas que sao **decomponiveis** em sub-valores cada qual com
sua propria nature:

| ID | Tipo | Decomposicao |
|---|---|---|
| CP-DATETIME | **datetime ISO** | `2026-05-24T09:30:45-03:00` -> date (templated+incremental) + time (templated+incremental) + tz (enumerated) |
| CP-ENDERECO | **Endereco BR** | `Rua X, 123, Bairro Y, Cidade Z - UF, CEP NNNNN-NNN` -> rua (templated) + numero (incremental) + bairro/cidade/UF (enumerated) + CEP (templated) |
| CP-MONEY | **Monetario com moeda** | `R$ 12.345,67` -> currency (enumerated) + amount (numeric) |
| CP-VERSION | **Semver** | `1.2.3-rc.4+build.5` -> major.minor.patch (3 incrementals) + pre-release (templated) + build (templated) |

## Hipoteses derivadas (a registrar em roadmap)

| ID | Hipotese | Datasets alvo | Compressao estimada |
|---|---|---|---|
| H-TM-01 | CPF pre-tx (omit `.`/`-` + check digits) reduz bytes -25% | D13 CPF, datasets reais financeiros futuros | -25 a -30% |
| H-TM-02 | IPv4 pre-tx (omit `.` + slots numericos) reduz -60% | Logs com IP, NetFlow exports | -50 a -70% |
| H-TM-03 | Telefone pre-tx (detect mask + extract digits) reduz -25% | CRMs, datasets de contato | -20 a -30% |
| H-TM-04 | CNPJ pre-tx similar a CPF reduz -28% | Datasets fiscais BR | -25 a -30% |
| H-TM-05 | MAC pre-tx (omit `:` + 6 bytes) reduz -65% | Logs de rede, IoT exports | -60 a -70% |
| H-TM-06 | IBAN pre-tx (omit espacos + check) reduz -15% | Datasets bancarios EU | -10 a -20% |
| H-TM-07 | Composite datetime aplicacao successiva de naturezas reduz -50% vs M10 raw | D11a-h, TPC-H date cols | -30 a -60% (depende cadencia) |
| H-LR-01 | LR-FLOAT-PREC com precisao=2 reduz -30% vs M10 em decimais cientificos | Wine Quality (futuro), Beijing PM2.5 (futuro) | -20 a -40% |
| H-LR-02 | LR-MONETARY com round automatico = -15% vs M10 em Online Retail UnitPrice | Online Retail (futuro) | -10 a -25% |

## Composicao de naturezas (ja' planejada em META-TYPE-ENCODERS)

Exemplo CPF formatado: `123.456.789-09`

```
Camada 1 — Templated (extract mask):
  template: "NNN.NNN.NNN-DD"
  slots:    ["123", "456", "789", "09"]

Camada 2 — Composite (split em campos semanticos):
  digits:   ["1234567890"]
  check:    "09"  (regeneravel via Camada 3)

Camada 3 — Checked (eliminate check):
  encoded:  "1234567890"  (10 digit base, check regen no decode)

Camada 4 — Incremental (se serie sequencial):
  base:     "1234567880"
  delta:    +10

Total encoded: ~3-4 bytes vs 14 raw = -75%
```

Pipeline natureza-a-natureza: composicao explicita no encode +
inversa no decode. **Pre-requisito**: contract de cada nature
encoder (input/output bem definidos).

## Conexao com infraestrutura atual (welded)

**Hoje (M10 + ADR-0014)**:
- `ColumnFeatures` ja' produz `is_numeric`, `avg_len`, `cardinality`
- `detect_cadence` regra 2 (numeric+high-card) ja' captura **parte**
  de TM-IP4 (octetos sao numericos) — provavelmente OK
- `analyze_column` poderia ser estendido com `detect_pattern` (regex
  matching pra `^\d{3}\.\d{3}\.\d{3}-\d{2}$` -> CPF, etc.)
- `SideOutputs` recipiente ja' pronto pra capturar info de naturezas
  detectadas

**Reaproveitamento esperado**:
- Schema builder (T-CODE-SCHEMA-BUILDER) consome ColumnFeatures +
  detect_pattern -> produz schema com naturezas detectadas por coluna
- Cada nature encoder eh modulo separado (`src/tcf/natures/templated.py`,
  `checked.py`, `lossy.py`)
- Encoder principal `encode()` dispatcha pre-tx baseado em schema:
  ```python
  schema = build_schema(data)
  # Detectou CPF em coluna "doc"
  # Pipeline: pre_tx_cpf -> encode canonical -> post_tx_cpf no decode
  ```

## Decisao / criterio de reabertura

META-TYPE-ENCODERS estabeleceu criterio: T02-T07 reabrem quando
"casos real-world onde Pacote 1 + ADR-0008 nao bastem". Esse criterio
foi reforçado por:

- **Pacote 2 escape**: refutado (1.13% << 5%)
- **Pacote 5 enumerated**: refutado (M10 ja' captura via dedup)
- **Naturezas raras #5/#8**: refutadas em datasets gerais

**Conclusao**: M10 cobre **naturezas comuns implicitamente**. Naturezas
templated/checksummed/lossy provavelmente so' valem em datasets
**dedicados** com presença significativa (>= 20% das colunas):

| Dataset alvo | Natureza dominante | Probabilidade ganho >=15% |
|---|---|---|
| **Online Retail** (T-DATA-1, download pendente) | TM-EAN (StockCode), LR-MONETARY (UnitPrice .99/.95/.50) | Alta |
| **Beijing PM2.5** (T-DATA-1, download pendente) | LR-FLOAT-PREC (DEWP/TEMP/PRES) | Alta |
| **Wine Quality** (T-DATA-1, download pendente) | LR-FLOAT-PREC (features quimicas) | Media-Alta |
| Datasets fiscais BR (futuro) | TM-CPF, TM-CNPJ | Alta |
| Datasets de rede (futuro) | TM-IP4, TM-MAC | Alta |
| Datasets de contato (futuro) | TM-FONE-BR, CP-ENDERECO | Media |

**Pre-requisito de reabertura**: owner rodar T-DATA-1 scripts +
medir baseline M10 vs natureza alvo (sub-exp tipo `01-caracterizacao`).
Se ganho >= 15% em 2+ datasets, abrir sub-pacote.

## See also

- [Taxonomia formal META-TYPE-ENCODERS](../../../../tickets/META-TYPE-ENCODERS.md) — T02 templated, T04 checked, T05 composite
- [Naturezas numericas (2026-05-23)](naturezas-numericas-2026-05-23.md) — #5 range, #8 arredondamento, #10 lossy
- [T-CODE-SCHEMA-BUILDER](../../../../tickets/T-CODE-SCHEMA-BUILDER.md) — produz schema rico
- [Roadmap hipoteses](roadmap-hipoteses.md) — H-TM-* a adicionar
- [Datasets pendentes T-DATA-1](../../../../tickets/T-DATA-1-datasets-financeiros-cientificos.md) — download pendente owner
