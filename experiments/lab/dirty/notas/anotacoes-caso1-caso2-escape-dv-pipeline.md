# Anotações: caso 1 (escape) + caso 2 (base94) — status feito/fechado/não-feito

**Data**: 2026-06-25. Origem: inspeção dos outputs CPF (owner reconheceu que "algumas
estavam feitas"). Registro do STATUS de cada item levantado, pra não re-investigar.
Foco da sessão segue sendo o **fluxo** (H-NAT-SPEC); estes são itens ADJACENTES.

## Registro de status

| item | onde aparece | status | detalhe |
|---|---|---|---|
| **escape-DEDUÇÃO** (por-ocorrência, `digit>node_count`) | caso 1, caso 2.2 | **FECHADO** (insufficient-gain) | Pacote 2 (META-ESCAPE-DEDUCTION). 15.7% sint MAS 0.13–1.13% real-world → closed. |
| **escape-INVERTIDO (EI)** (flip GLOBAL por header) | caso 1, caso 2.2 | **ABERTO, VIÁVEL** ⚠️ corrige rejeição | DISTINTO da deduction (global vs por-ocorrência; não depende de node_count). Medido: caso1-raw 18.8%, suíte 9.2% (UUID 12.9%). Ver [hipotese-escape-invertido-EI.md](hipotese-escape-invertido-EI.md). |
| **DV-drop care** (não dropar DV inválido) | caso 2.1 | **FEITO** | `classify_value`: DV inválido → `check_invalid` → não-compressible → **fallback literal** (`_`+v) mantém o CPF. Idem `format_unmasked` (11 díg crus). |
| **alfabeto base94 livre-de-conflito** (evitar chars que precisam escape) | caso 2.2 | **NÃO FEITO** (candidato micro) | escolher BASE94 sem `\`/`*`/`~`/`:` e sem começar igual a índice → menos escapes. Adjacente à escape-deduction (mas estrutural, não dedutivo). Anotar como micro-opt. |
| **parallelismo MULTI-coluna** (ProcessPoolExecutor) | — | **FEITO** | `multi/parallel.py` — encoda colunas em paralelo (HOST). Byte-idêntico ao serial. |
| **producer-consumer INTRA-coluna** (filtro∥OBAT, fila) | caso 2.3 | **NÃO FEITO** (deferido v2.0) | = **V2-J streaming** (ADR-0018): cada etapa entrega o mais cedo possível, otimiza LATÊNCIA (time-to-first-byte). É o **modo 3 (bypass)** do fluxo. |

## Por que a escape-deduction fechou (pra não reabrir sem motivo)
O ganho era enorme em sintéticos CONSTRUÍDOS pra exibi-lo (D11a-h, 15.7%) mas evaporou
em real-world (0.13–1.13%) — padrão clássico do anti-incidente 2026-05-21 (sub-exp em
dataset construído pra testar a hipótese não generaliza). Reabrir só com dado real onde
digit-runs grandes (> node_count) sejam frequentes E o peso do `\` seja material.

## Avaliação do producer-consumer (caso 2.3) — para o desempenho
- **Sã e determinística**: filtro (classify+strip+base94) é INDEPENDENTE por-valor →
  paralelizável; OBAT é SEQUENCIAL (online, referencia anteriores) → consumidor ordenado.
  Filtro-paralelo → fila-ordenada → OBAT-consumidor. Bytes idênticos (filtro não reordena).
- **Ganho de throughput LIMITADO**: o gargalo global é o **HCC** (`_detect_compositions`
  = 64.5% do encode, DEPOIS do OBAT). Overlapar filtro+OBAT não toca o HCC → Amdahl. E pra
  filtro barato (CPF), o OBAT já é o limite do par filtro+OBAT.
- **Valor real = LATÊNCIA/streaming** (V2-J), não throughput. Premissa do owner ("OBAT mais
  lento que o filtro") correta, mas OBAT ≠ gargalo global.

## Conexão com o FLUXO (H-NAT-SPEC)
- caso 1 (escape) e caso 2.1 (DV) são adjacentes — não o núcleo do fluxo.
- caso 2.3 (producer-consumer) **É o modo 3 (bypass)** = V2-J streaming (deferido).
- Cross-links: [hipotese-filtro-natureza-especulativo.md](hipotese-filtro-natureza-especulativo.md),
  [META-ESCAPE-DEDUCTION](../../../../tickets/META-ESCAPE-DEDUCTION.md),
  [ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md) §V2-J.
