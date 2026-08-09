# Resultado — triagem das 7 hipóteses restantes de data

**2026-08-09 · dirty/esboço · `n=600`, RT conferido em todo wire, 0 falhas**

Reavaliação pedida pelo owner: *"veja se tem mais algum aspecto interessante que talvez não
tenhamos visto"*. Sete hipóteses saíram da reavaliação; a triagem abaixo diz o destino de
cada uma. Números completos em [`outputs/medicoes.md`](outputs/medicoes.md).

---

## O placar

| hipótese | resultado | destino |
|---|---|---|
| **H6 — alvo DELTA de coluna** | teto de **3116 B** no espalhado-ordenado (5,8×) | **→ lab próprio** — a maior oportunidade restante |
| **H2 — dias úteis** | spec 1590 B; delta naive **233 B** (6,8×) | **→ junto com H6** — mesmo mecanismo resolve |
| **H1 — spec→bN no candidato** | lacuna cresce com k: 19 → 70 → **298 B** | **→ weld pequeno** (mesma classe do fix do baseline) |
| H3 — sentinelas | degrada com graça: +24 B por sentinela | registrado; a válvula já cuida |
| H4 — quase-null | spec ainda ganha até 99% null | confirmado OK; nada a fazer |
| H5 — resolução mista | válvula segura; `YYYY-MM` pediria spec irmão | fila do `T-SPEC-PARSE-X-ALVO` |
| **H7 — colunas irmãs** | lacuna de **89 B em 2959 (3%)** | **morta** — não compensa |

## As duas que importam

### H6+H2 — o alvo DELTA é a maior oportunidade que sobrou

O spec soldado (ordinal) depende do `*N+M|`, que só come **delta uniforme**. Dois regimes
realistas quebram isso:

| regime | com spec (hoje) | delta naive | fator |
|---|---:|---:|---:|
| **dias úteis** (delta `[1,1,1,1,3]`) | 1590 B | **233 B** | 6,8× |
| dias úteis + feriados | 1889 B | **339 B** | 5,6× |
| **espalhado-ordenado** (deltas pequenos irregulares) | 3759 B | **643 B** | 5,8× |

O mecanismo: o delta transforma o **período** em texto repetitivo (`1,1,1,1,3,1,1,1,1,3…`),
que o core come com RLE de linha — sem precisar que o delta seja uniforme.

**O atrito é de protocolo**: a nature é per-valor (`encode_value(v)`), e delta precisa do
vizinho. É um transform de **coluna**. O lab próprio decide o design; os candidatos óbvios:
transform de coluna no protocolo da nature, ou vitaminar o próprio seq-RLE pra período
(`*N+[1,1,1,1,3]|`), que beneficiaria qualquer coluna numérica, não só data.

### H1 — o candidato da nature não consulta o bN

Consertamos o **baseline** (o FLOOR via o bN); o **candidato** tem a mesma lacuna: a coluna
transformada vai pro `_encode_column` cru, sem os candidatos bN. Em data de baixa
cardinalidade, o ordinal encolhe o domínio (6 chars vs 10) e o bN pegaria:

| k | hoje (spec recusa) | ordinal→encode() com bN | lacuna |
|---:|---:|---:|---:|
| 5 | 364 | 345 | 19 B |
| 12 | 529 | 459 | 70 B |
| 60 | 976 | **678** | **298 B** |

Weld pequeno — trocar `_encode_column(transformed)` por um caminho que consulte os mesmos
candidatos da rota flat. **Precisa de aprovação (mexe em `src/tcf`).**

## A que morreu, e por quê vale registrar

**H7 (colunas irmãs)**: a intuição era forte — `created/updated/shipped` correlacionadas, o
delta entre colunas é pequeno. Medido: multi-col independente 2959 B, delta-entre-colunas
naive 2870 B. **Lacuna de 3%.** A razão: as colunas irmãs, cada uma ordenada-ish, já
comprimem quase tão bem sozinhas quanto os deltas. Cross-column delta pra data **não paga o
design** — e isso poupa um mecanismo inteiro.

## Miúdos que ficam registrados

- **Sentinela é data válida** (`9999-12-31` parseia!) — vira ordinal gigante e quebra a
  corrida em duas: +24 B cada. O `0000-00-00` do MySQL **não** parseia (ano 0) e cai na
  válvula: +30 B. Com 5% de sentinelas o spec ainda ganha 4× do sem-spec. Nada a fazer no
  código; o guia de normalização pode mencionar.
- **Quase-null**: 95% → spec ganha 17%; 99% → ganha 8%; um-só-valor → recusa e empata.
  Comportamento correto em todo o espectro.
- **`YYYY-MM` puro**: o spec recusa a coluna inteira (não parseia) — seguro, mas um
  `SPEC_DATA_ANO_MES` irmão seria trivial quando o `T-SPEC-PARSE-X-ALVO` acontecer.

## Próximo passo (conforme o fluxo combinado)

1. **Lab próprio do alvo DELTA** (H6+H2) — sintético controlado, variações de período e
   ruído, e a decisão de design (transform de coluna × seq-RLE periódico).
2. **H1** é weld curto — aguarda aprovação do owner.
3. Depois dos dois: **lab clean em massa** consolidando data inteira (o EXP da família
   data), no molde do EXP-016.
