# Sub-exp 08 — IP TCU-Delta (report)

**Data**: 2026-05-24
**Status**: completed — **achado dramatico (variante C subnet 1.71%)** + RT FAIL identificado em mixed-format

## Achado central

**Variante C (padded + strip dots) com D-IP-subnet:**
- 1000 IPs em subredes /24
- raw: 13,400 bytes
- **TCF: 229 bytes (1.71% ratio)** — 60x melhor que variante B (50%)
- HCC seq-RLE detecta cadence_detected=True + 11 seq_rle_runs

**Por que tao dramatico?** A padding com leading zeros CRIA estrutura
que HCC detecta:
- `057012140000`, `057012140001`, `057012140002`, ... (12 chars fixos)
- Primeiros 9 chars identicos por subrede; ultimos 3 chars seq
- HCC seq-RLE compacta em template + delta
- 1000 IPs viram 1 template + 10 markers — 229 bytes total

## Tabela de resultados (9 datasets × 3 variantes)

| Dataset | A (M10) | B (32-bit base94) | C (padded 12-digit) | Vencedor |
|---|---:|---:|---:|---|
| uniform | 18159 (127%) | **7607 (53%)** | 14652 (102%) | B (-47%) |
| **subnet** | 15747 (118%) | 6683 (50%) | **229 (1.71%)** ⚡⚡ | **C (-98%)** |
| mixed | 19003 (125%) | 7608 (50%) RT FAIL ❌ | 14632 (96%) RT FAIL ❌ | A (RT OK mas pior) |
| corrupt | 18131 (127%) | **8081 (57%)** | 14771 (103%) | B (-43%) |
| edge-single | 18 (129%) | **7 (50%)** | 14 (100%) | B |
| edge-allsame | 24 (0.17%) | **13 (0.09%)** | 20 (0.14%) | B (RLE em todos) |
| edge-allcorrupt | **17249 (128%)** | 17953 (133%) | 17953 (133%) | A (RT preserva) |
| extra-large10k | 175734 (123%) | **76196 (53%)** | 146412 (103%) | B (-47%) |
| extra-hostile | **13026 (104%)** | 8218 (65%) RT FAIL ❌ | 11386 (91%) RT FAIL ❌ | A (RT preserva) |

## H1 — re-examinada no contexto IP

Em CPF, H1 (base-encode mascara padroes) foi REFUTADA: B vence.
Em IP, H1 **se confirma parcialmente**: padding com leading zeros (C)
cria estrutura visivel que HCC detecta e bate B dramaticamente em
subnet.

**Lesson**: a "visibilidade" eh contexto-dependente. CPF random nao tem
clustering significativo; IP subnet tem clustering OBVIO (sub-redes /24).

## H3 — categoria abstraida

IP NAO se encaixa em TemplatedCheckedSpec do sub-exp 07 (CPF/CNPJ)
porque:
- Sem check digit (check_fn=None)
- Slots de comprimento variavel (octeto 0-255 = 1-3 chars)

Categoria proposta: **TCU-NoCheckVarLength** (sibling de TCU-CheckedFixedLength).

Spec separado necessario; nao reusa TemplatedCheckedSpec as-is.
Generalizacao requer abstrair "slot behavior" e "length policy".

## RT FAIL identificado: normalizacao silenciosa

**D-IP-mixed** (50% padded `192.168.001.001` / 50% canonical `192.168.1.1`):
- B e C: ratio fica em ~50%/96% mas **RT 572/1000** ❌
- Causa: encoders normalizam padded -> canonical, perdem leading zeros

**D-IP-extra-hostile** (mix de formatos + IPv6 + vazios):
- Mesmo problema (824/1000 RT)

**Implicacao pratica**: encoders C/B precisam detectar padded form
e fazer fallback literal — mesma policy do sub-exp 05 mas com novo
status `format_padded_zeros`.

Sub-exp 09 candidato: padding-aware fallback policy.

## Vencedor recomendado por perfil

- **Datasets random/sem clustering**: B (32-bit base94) — ~50% ratio
- **Datasets com subnet structure**: C (padded 12-digit) — ate' 1.71%!
- **Datasets dirty (corrupt/hostile/mixed)**: A (M10 puro) ate' fallback
  marker correto. Variantes B/C com RT FAIL silencioso sao perigosas.

**Heuristica schema_builder Fase 3 estendida**:
1. Detectar formato dominante (canonical vs padded)
2. Se canonical-only: tentar B (base94)
3. Se padded ou subnet-detected: tentar C
4. Fallback A se nada compensar

## SlotBehavior — implicito vs explicito

Hipotese de design SlotBehavior explicito (per-octeto, com delta no
ultimo): nao foi necessario implementar diretamente. Padding (C) +
HCC seq-RLE alcanca o mesmo efeito empiricamente:

- C subnet: cadence_detected=Y, 11 seq_rle_runs, 1.71%
- C uniform: cadence_detected=Y, 500 seq_rle_runs, 102%

HCC ja' captura "delta no slot" implicitamente quando o input eh
templated visivel. **SlotBehavior explicito redundante em TCF M10.**

## Outputs visiveis (auditoria)

```
out_tcf/
├── A/   (M10 puro, 9 datasets)
├── B/   (base94 6-char, 9 datasets + mismatches.txt em mixed/hostile)
└── C/   (padded 12-digit, 9 datasets + mismatches.txt em mixed/hostile)
```

Cada variante tem `.tcf` + `decoded-sample15.txt` por dataset.

## Conclusoes

1. **Subnet structure ativa HCC seq-RLE catastroficamente bem** (C 1.71%)
   — a maior surpresa positiva do dirty lab CPF/CNPJ/IP
2. **B (base94) eh seguro generico** (~50% em random/uniform)
3. **A (M10 puro) eh fallback universal** mas piora bytes em IP
4. **RT FAIL em mixed/hostile** — fallback marker precisa cobrir
   padded zeros + outros formatos alternativos
5. **SlotBehavior explicito desnecessario** — padding visivel ja' explora
   HCC seq-RLE
6. **H3 amplia**: categoria splits em sub-tipos por estrutura de slot
   (CheckedFixedLength vs NoCheckVarLength vs Delta-prone)
