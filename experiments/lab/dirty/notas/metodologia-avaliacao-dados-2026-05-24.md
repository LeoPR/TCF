---
title: Metodologia de avaliacao de dados — mapeamento academico
type: reference-note
status: rascunho
tags: [methodology, literatura, data-quality, dirty-lab, testing, benchmarks]
created: 2026-05-24
related:
  - experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/README.md
  - experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md
  - README.methodology.md
---

# Metodologia de avaliacao de dados — mapeamento academico

> Owner pediu (2026-05-24) reavaliar a metodologia "dados comportados
> vs deviating vs lixo" contra a literatura — provavelmente ja' eh
> framework estabelecido pra testar sistemas que lidam com dados.
> Esta nota mapeia nossa pratica dirty lab a referencias academicas.

## Frameworks estabelecidos relevantes

### 1. Boundary Value Analysis (Beizer 1995)

Testar **just inside, on, just outside** dos limites do dominio.
- Aplicacao em compressao: testar com N=0, N=1, N=infinito;
  valores na borda do alfabeto (todos iguais, todos diferentes,
  ASCII vs UTF-8 multi-byte).

Referencia: Beizer, B. (1995). *Black-Box Testing: Techniques for
Functional Testing of Software and Systems*. Wiley.

### 2. Equivalence Class Partitioning (Myers 1979)

Particionar input space em classes onde "se um valor funciona, todos
funcionam". Testar 1 valor por classe.
- Aplicacao: classes de CPF — formatados com mascara, sem mascara,
  com check valido, com check invalido, com chars invalidos, vazios.
  Cada classe = 1 sub-tipo de fallback_reason.

Referencia: Myers, G. J. (1979). *The Art of Software Testing*. Wiley.

### 3. Mutation Testing (DeMillo, Lipton, Sayward 1978)

Injetar **falhas sistematicas** controladas no input pra verificar
robustez do sistema.
- Aplicacao: nosso `corrupt_check` / `corrupt_format` /
  `corrupt_chars` / `corrupt_length` sao **mutacoes** sistematicas
  de um CPF valido. Mede como sistema reage a cada tipo.

Referencia: DeMillo, R. A., Lipton, R. J., & Sayward, F. G. (1978).
"Hints on Test Data Selection: Help for the Practicing Programmer".
*Computer*, 11(4), 34-41.

### 4. Property-Based Testing (Hughes, QuickCheck 2000)

Gerar inputs aleatorios e validar **invariantes** (e.g., RT
byte-canonical). Mais robusto que cases manuais.
- Aplicacao: Hypothesis (Python) poderia gerar CPFs aleatorios e
  validar `decode(encode(v)) == v` em escala (e.g., 10^6 cases).

Referencia: Claessen, K., & Hughes, J. (2000). "QuickCheck: A
Lightweight Tool for Random Testing of Haskell Programs". *ICFP*.

### 5. Wang & Strong — Data Quality Dimensions (1996)

Framework canonico de qualidade de dados em 4 categorias:
- **Intrinsic**: accuracy, objectivity, believability, reputation
- **Contextual**: relevancy, timeliness, completeness, appropriate
  amount
- **Representational**: interpretability, ease of understanding,
  representational consistency, concise representation
- **Accessibility**: accessibility, access security

Referencia: Wang, R. Y., & Strong, D. M. (1996). "Beyond Accuracy:
What Data Quality Means to Data Consumers". *Journal of Management
Information Systems*, 12(4), 5-33.

### 6. Rahm & Do — Taxonomia de Dirty Data (2000)

Taxonomia influente: classifica problemas em **single-source** vs
**multi-source** e **schema-level** vs **instance-level**.
- Single-source: missing values, misspellings, embedded values,
  contradicting values
- Multi-source: nomenclatura inconsistente, structural conflicts
- Aplicacao: nossos `D-CPF-corrupt` casos = single-source instance-level
  errors. `D-CPF-mixed` = multi-source style (2 formatos coexistindo).

Referencia: Rahm, E., & Do, H. H. (2000). "Data Cleaning: Problems
and Approaches". *IEEE Data Engineering Bulletin*, 23(4), 3-13.

### 7. Kim et al. — Taxonomy of Dirty Data (2003)

Refinamento de Rahm & Do. 33 tipos de dirty data em hierarquia:
missing data, wrong data, non-standard format, duplicated, abbreviated.
- Aplicacao: nosso `format_unmasked` = "non-standard format" (Kim 2.1);
  `check_invalid` = "wrong data — fail integrity constraint" (Kim 3.4);
  `length_wrong` = "syntactic violation" (Kim 1.1).

Referencia: Kim, W., Choi, B. J., Hong, E. K., Kim, S. K., & Lee, D.
(2003). "A Taxonomy of Dirty Data". *Data Mining and Knowledge
Discovery*, 7, 81-99.

### 8. ISO/IEC 25012 — Data Quality Model (2008)

Norma internacional: 15 caracteristicas de qualidade de dados,
organizadas em **inherent** (objetivas do dado) e **system-dependent**
(dependem do sistema).
- Inherent: accuracy, completeness, consistency, credibility,
  currentness
- System-dependent: accessibility, compliance, confidentiality,
  efficiency, precision, traceability, understandability, availability,
  portability, recoverability

**Aplicacao direta** em NatureApplyStats:
- `accuracy` = % valores que passam regex + check
- `completeness` = % non-empty
- `consistency` = % no formato dominante
- `compliance` = % adere a spec estrita (CPF + mod-11 valido)

Referencia: ISO/IEC 25012:2008 *Software engineering — Software
product Quality Requirements and Evaluation (SQuaRE) — Data
quality model*.

### 9. Canterbury, Calgary & Silesia Corpora (compressao)

Datasets canonicos pra benchmarking de compressao:
- **Calgary Corpus** (Witten, Bell, Cleary 1988): 14 arquivos
  text/binary, historico
- **Canterbury Corpus** (Arnold, Bell 1997): replacement modernizado
  do Calgary com diversidade controlada
- **Silesia Corpus** (Deorowicz 2003): 6 arquivos grandes (>5MB cada)
  pra benchmarks modernos
- **Maximum-compression.com** (Bergmans, ongoing): tracking publico
  por arquivo

**Aplicacao**: TCF deveria reportar bytes em pelo menos 1 desses
corpora pra ser comparavel academicamente. **Pendente** (todos nossos
benchmarks atuais sao em datasets proprios — synthetic + TPC-H +
Adult Census).

Referencias:
- Bell, T., Cleary, J. G., & Witten, I. H. (1990). *Text Compression*.
  Prentice Hall.
- Arnold, R., & Bell, T. (1997). "A Corpus for the Evaluation of
  Lossless Compression Algorithms". *DCC*.
- Deorowicz, S. (2003). *Universal lossless data compression
  algorithms*. PhD thesis.

### 10. Fuzzing (Miller, Fredriksen, So 1990)

Random + adversarial input testing. **Garbage in -> test that
system doesn't crash**.
- Aplicacao: nossos `D-CPF-extra-hostile` (75% fallback, mix de tudo)
  eh estilo fuzzing — testa que encoder/decoder lidam sem crash mesmo
  com input desfavoravel.

Referencia: Miller, B. P., Fredriksen, L., & So, B. (1990). "An
Empirical Study of the Reliability of UNIX Utilities". *Comm. ACM*,
33(12), 32-44.

### 11. TPC Benchmarks (TPC.org, 1988-present)

Sintetico-mas-realistico. Padrao da industria pra database/data
warehouse.
- TPC-C: OLTP transactional
- TPC-H: ad-hoc analytics (ja' usamos)
- TPC-DS: complex decision support

Mais cobertura academica de "realistic synthetic" no mundo de
sistemas que lidam com dados.

## Mapeamento do nosso dirty lab CPF a literatura

| Nosso dataset | Etapa interna | Framework academico equivalente |
|---|---|---|
| D-CPF-uniform | 1 (ilustrativo) | Equivalence class "valid format" (Myers); Canterbury "happy path" |
| D-CPF-clustered | 1 (ilustrativo) | TPC-like sintetico-realista (clustering administrativo simula DB real) |
| D-CPF-mixed | 1 (ilustrativo) | Multi-source schema conflict (Rahm & Do); 2 equivalence classes coexistindo |
| D-CPF-corrupt | 1 (ilustrativo) | **Mutation testing** (DeMillo) com 4 mutacoes sistematicas (corrupt_check, _format, _chars, _length) |
| D-CPF-edge-single | 3 (borda) | Boundary Value Analysis (Beizer) — N=1 |
| D-CPF-edge-allsame | 3 (borda) | Boundary — cardinalidade=1, redundancia maxima |
| D-CPF-edge-allcorrupt | 3 (borda) | Boundary — 100% mutado, dimensoes ISO 25012 (accuracy=0) |
| D-CPF-extra-large10k | 4 (extrapolacao) | Scale/stress testing |
| D-CPF-extra-hostile | 4 (extrapolacao) | **Fuzzing** (Miller 1990) — adversarial mix |

## Aplicacao em NatureApplyStats (sub-exp 06)

Vou adotar dimensoes de **ISO/IEC 25012** mapeadas pro contexto de
encoders por natureza:

```python
@dataclass
class NatureApplyStats:
    nature: str
    n_total: int
    n_applied: int      # n_compressible
    n_fallback: int

    # Apply-time
    apply_rate: float                     # n_applied / n_total
    fallback_reasons: dict[str, int]      # taxonomia Kim et al. 2003

    # Dimensoes ISO/IEC 25012 (inherent)
    accuracy_rate: float                  # % strictly valid (regex + check)
    completeness_rate: float              # % non-empty
    consistency_rate: float               # % no formato dominante
    compliance_rate: float                # % adere spec rigida (== apply_rate sem fallback inline)
```

## Convencao adotada

Daqui pra frente, datasets sinteticos em dirty lab devem:

1. **Citar framework** academico em comentario do gerador (ex: "Etapa
   3 borda — Beizer Boundary Value Analysis: N=1, N=large").
2. **Stats em ISO 25012** quando produzir relatorio agregado.
3. **Comparar** com pelo menos 1 corpus canonico (Canterbury/Silesia)
   quando avaliar compressao real (atualmente nao fazemos — debt
   declarado).

## Conexao

- [Naturezas templated](naturezas-templated-2026-05-24.md)
- [CPF dirty lab](../old/welded/2026-05-24-cpf-templated-checked/README.md)
- [README.methodology cross-projeto](../../../../README.methodology.md)
- [CLAUDE.md secao "Antes de declarar confirmada-empirica"](../../../../CLAUDE.md) — usa Wohlin 2012 threats to validity, Brunswik 1956 ecological validity
