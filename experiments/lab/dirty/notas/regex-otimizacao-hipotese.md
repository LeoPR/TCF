# Hipótese: regex como frente de otimização — AVALIADA (prioridade baixa)

> **ENCERRADA (2026-07-09, T-CLEAN-3 T3-b)** — levantada, avaliada read-only e fechada no mesmo dia
> (2026-06-25): "não é frente de otimização significativa". A frente real do hotspot
> (`_detect_compositions`) é o [ADR-0020](../../../../docs/adr/0020-cython-optional-accelerator.md)
> (Cython opcional). Condições de reabertura preservadas no corpo.

**Data**: 2026-06-25. **Origem**: hipótese do owner — regex aparece em vários cenários
de avaliação no código; perspectivas: precompilar, concatenação/alternação, regex no
decode como acelerador. **Status**: avaliada read-only; **não é frente significativa**.

## Uso de regex hoje (src/tcf — mínimo e já otimizado)
- `natures/templated_checked.py`: `_CPF_RE`, `_CNPJ_RE` — `re.compile` no MÓDULO
  (precompilado), usados em `classify_value` (`self.regex.match(v)`).
- `natures/templated_padded.py`: `_IPV4_RE` — precompilado (classify/encode/decode).
- `multi/split.py`: `_DIGITS = re.compile(r"(\d+)")` — precompilado.
- **Core NÃO usa regex**: OBAT (LCP/LCS contra strings anteriores) e HCC (parser de
  marcadores `^ * , ~ .. \`) são algoritmos especializados char-a-char/índice.

## Avaliação das perspectivas
- **Precompilar**: já feito (todo regex é `re.compile` no módulo). Sem ganho.
- **Concatenação/alternação** (`(CPF|CNPJ|IP)`): só ajudaria em AUTO-DETECT (classificar
  um valor contra vários specs de uma vez) — mas auto-detect foi rejeitado (ADR-0015);
  hoje o spec da coluna é conhecido (1 regex por coluna). Nicho sem demanda.
- **Regex no decode (acelerador)**: não encaixa. O decode HCC é parser COM ESTADO
  (resolve refs, expande ranges/aliases) — não é gramática regex-tokenizável. E o decode
  NÃO é hotspot: o profiling (ADR-0020) apontou `_detect_compositions` no ENCODE (64.5%),
  que o Cython já acelera. Tokenizar marcadores com regex não troca o trabalho stateful.

## Veredicto
Regex já é usado de forma ótima onde encaixa (natures/split, precompilado). Os caminhos
quentes (OBAT/HCC) não são regex-shaped — algoritmos especializados ganham deles. **Não é
frente de otimização significativa.** Onde regex É a ferramenta certa (validação de formato
de natures), seguir precompilando. Reabrir só se surgir natures com formato complexo OU se
o profiling apontar um caminho regex-tokenizável virando hotspot.

Cross-link: [ADR-0020](../../../../docs/adr/0020-cython-optional-accelerator.md) (acelerador
do hotspot real), [specs-capacity-map.md](specs-capacity-map.md) (natures/regex).
