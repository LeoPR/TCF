# 0017 — Format spec v1.0 frozen + versioning policy

**Status**: proposed
**Date**: 2026-05-27
**Deciders**: project owner
**Tags**: format, versioning, v1.0, backwards-compat, stable-api

## Context and Problem Statement

TCF format atual (`#TCF.6`) tem 16 ADRs accepted (0001-0016), suite
de regressao formal (259 tests, [test_regression_v1_baseline.py](../../tests/test_regression_v1_baseline.py)),
validacao real-world em 12+ datasets (Adult, TPC-H 9 tabelas + 3 UCI
novos), API estavel via [ADR-0014](0014-unified-api-side-outputs.md).

**Pendente para v1.0 estavel**: commitment de **back-compat** —
clientes que escrevem `from tcf import encode, decode` hoje devem
funcionar identicamente em qualquer versao `1.x.y`.

Sem essa decisao explicita, format/API podem mudar a qualquer momento
e usuarios externos nao tem garantia.

## Decision Drivers

1. **Estabilidade pra adocao**: pesquisadores citando TCF em paper
   precisam de versao fixa que nao quebra
2. **Espaco pra extensoes**: features novas (Pacote 7 natures, Fase 2
   layered pipeline, streaming) devem caber em `1.x` ou `2.0`
3. **Migration path explicita**: se v2 quebrar, deve haver caminho
   documentado v1 → v2
4. **Distincao format vs API**: shebang versiona format (`#TCF.6`);
   semver versiona biblioteca (`1.0.0`)

## Considered Options

### Opcao A — Freeze tudo (format + API) em v1.0

Commitment forte: nenhuma mudanca em format ou API ate v2.0. Bug fixes
ok (1.0.x); features novas via API additive (1.x.0) sem alterar bytes
existentes. Format spec marker `#TCF.6` IMUTAVEL em v1.x; v2 introduz
`#TCF.7`.

**Pros**:
- Garantia maxima pra usuarios
- Paper/pesquisa pode citar `TCF 1.0.0` sem ambiguidade
- Suite regressao (test_regression_v1_baseline.py) ja' captura format

**Cons**:
- Bloqueia experimentos disruptivos sem version bump major
- Format change (ex: Layered Pipeline Fase 2 marker `*FALLBACK_X`)
  exige `#TCF.7` + v2.0.0

### Opcao B — Freeze API, deixar format extensivel

API publica (`encode`, `decode`, `SideOutputs`, `PipelineConfig`,
`SPEC_CPF`, etc.) imutavel; format pode adicionar markers novos
desde que decoder velho aceite (skip unknown).

**Pros**:
- Mais flexibilidade pra evolucao incremental
- Decoder forward-compat (graceful degradation)

**Cons**:
- "Skip unknown" e' complexo de implementar e testar
- Bytes de mesma data podem variar entre 1.x versions (quebra reproducibilidade)
- Confunde "qual versao gerou esse arquivo"

### Opcao C — Freeze nada, declarar "0.x experimental, sem garantias"

Manter v0.6+ ate' projeto maduro, sem commitment ainda.

**Pros**:
- Maxima liberdade
- Sem custo de manutencao back-compat

**Cons**:
- Bloqueia adocao academica
- Paper nao pode citar versao estavel
- Sem incentivo pra fechar/estabilizar

## Decision Outcome

**Chosen option: A — Freeze format + API em v1.0**.

Razao: TCF ja' tem maturidade tecnica (16 ADRs, 259 tests, validacao
real-world em 12+ datasets). Falta apenas commitment formal. Opcao B
adiciona complexidade (forward-compat decoder) sem ganho proporcional;
Opcao C bloqueia adocao.

### Policy

**Format**:
- `#TCF.6` = v1 stable, IMUTAVEL ate' v2.0.0
- Nenhum byte de arquivo TCF v1 muda entre versoes 1.x.y
- Markers novos (ex: `*FALLBACK_X` da Fase 2 layered) requerem `#TCF.7` e v2

**API publica** (re-exportada via `from tcf import ...`):
- `encode`, `decode`, `SideOutputs`, `PipelineConfig`, `build_schema`,
  `TableSchema`, `ColumnSchema`, `TemplatedCheckedSpec`,
  `TemplatedPaddedSpec`, `SPEC_CPF`, `SPEC_CNPJ`, `SPEC_IP`
- Assinatura imutavel ate' v2.0.0
- Parametros novos: somente keyword-only com default que preserva
  comportamento atual (ex: `encode(data, *, novo_param=default)`)

**Public API enumeration test** (#5 — disciplina enforcement):
`tests/test_regression_v1_baseline.py` deve incluir test que asserta
`set(tcf.__all__) == EXPECTED_PUBLIC_API` com a lista exata acima.
Adicao OU remocao de exports requer atualizar test + ADR (versao).

**NAO faz parte da API publica** (#10 — clarification):

Modulos/simbolos abaixo sao **internal**, podem mudar em qualquer
1.x.y sem aviso:

- `tcf.encoder._encode_column`, `tcf._private_*` (prefix underscore)
- `tcf.multi._encode_multi`, `_encode_columns_parallel`, `_worker_*`
- `tcf.composicional.syntax.M8AVirtualRefsSyntax`, classes internas
- `tcf.composicional.hcc_seqrle.compare_for_seq`, `compact_body`,
  `expand_seq_marker`, `_is_uniform_delta` (helpers internos)
- `tcf.core.online.*`, `tcf.obat_shape.*` (modulos algoritmicos)
- `tcf.auto_cadence.*`, `tcf.auto_min_len.*`, `tcf.column_features.*`
- `tcf.schema.*` salvo `build_schema`, `TableSchema`, `ColumnSchema`
- `tcf.natures.templated_checked.*`, `templated_padded.*` salvo classes
  exportadas via `tcf.__init__`
- Estrutura interna de objetos retornados por `SideOutputs` (campos
  podem ganhar atributos novos; campos existentes preservados)

Usuarios que importam destes modulos diretamente assumem risco proprio.

**Semver mapping**:
- `1.0.x` — bug fixes
- `1.x.0` — features additive (Pacote 7 natures, schema_builder Fase 3,
  parallel API extensions)
- `2.0.0` — breaking changes (format change, API removal, marker novo
  no body)

**Bug fix policy** (#1 — distincao 1.0.x vs 2.0.0):

Nem todo "byte mudou" forca version bump major. Tres categorias:

1. **Critico (1.0.x permitido)** — output anterior era invalido,
   inutilizavel ou unreadable pelo decoder atual. Ex: fix `+-1,0` de
   [hcc_seqrle.py:207](../../src/tcf/composicional/hcc_seqrle.py#L207)
   produzia marker que decoder rejeitava com `ValueError`. Pre-fix
   ninguem podia ter dados legitimos nesse formato; bytes mudaram mas
   nao quebrou usuarios reais.
   - Test gate: arquivo pre-fix com bytes velhos NAO precisa decodar
   - CHANGELOG entry obrigatorio listando bytes afetados
2. **Cosmetic byte diff (exige 2.0.0)** — output anterior era valido
   e decodavel, mas mudou layout (ex: trocar `*N+1|` por `*N|+1`).
   Mesmo conteudo logico, bytes diferentes. Bloqueia regressao
   automatic e arquivos antigos.
3. **Performance optimization (1.0.x trivial)** — mesmo output, mais
   rapido. Snapshot test_regression nao muda byte; OK.

Em duvida: rodar `test_regression_v1_baseline.py` em arquivo gerado
em versao anterior. Se decode falha → categoria 1 (1.0.x ok). Se decode
ok mas bytes diferem → categoria 2 (2.0.0).

**Natures novas em v1.x** (#8 — clarification):

Adicionar `SPEC_LUHN`, `SPEC_MAC`, etc. em v1.x.0:
- **Sem `nature=` parametro**: bytes inalterados (default path nao toca
  no nature detection). Snapshot D1-D9, D17a, real-world preservados.
- **Com `nature=SPEC_NEW`**: bytes obviamente diferentes (e' o ponto
  do nature). Usuario opt-in explicito.

Regra de teste: cada nature nova exige `test_nature_<name>.py` com
RT + edge cases. Suite `test_regression_v1_baseline.py` continua com
default sem natures (preserva snapshot).

**Format vs library versioning**:
- Shebang `#TCF.N` = format version (incrementa em mudancas estruturais)
- Library `X.Y.Z` = semver da implementacao
- Mapping atual: TCF.6 ↔ tcf 1.0.x — qualquer 1.x.y produz/le' TCF.6

**Python version compat** (#2 — determinismo garantido):

v1.0 requires:
- **`python >= 3.10`** (declared in `pyproject.toml [project] requires-python`)
- Dict insertion order preserved (Python 3.7+, mas garantia formal so' 3.10+)
- `PYTHONHASHSEED=0` em CI pra determinismo reproducivel
- Sem dependencia de `set` ordering (codigo deve usar `sorted()` quando ordem importa)
- `conftest.py` no root setta `os.environ.setdefault("PYTHONHASHSEED", "0")`

Test matrix em CI: 3.10, 3.11, 3.12, 3.13. 322B INVARIANT deve bater
em todas as versoes.

Edge cases de encoding/decoding (regras explicitas):
- UTF-8 mandatory; BOM (`﻿`) preservado em values mas nao em
  shebang/header (parser strip se presente no inicio)
- LF only no output canonical; encoder NAO normaliza CRLF nos values
  (preserva bytes exatos do input pra RT)
- Codepoints fora BMP (emoji etc.) preservados via UTF-8 multibyte
- Empty values `""` codificados literalmente; empty list `[]` gera
  body vazio (xfailed em teste pre-v1.0 — comportamento esperado)
- Empty dict `{}` raises `ValueError` (ja' implementado em `multi.py`)

**CI gate enforcement** (#4 — sem ambiguidade):

- `.github/workflows/test.yml` (ou equivalente local) RODA
  `pytest tests/test_regression_v1_baseline.py` em **toda PR**
- Falha = block merge automatico
- Bypass requer:
  1. ADR novo declarando intencional (com justificativa)
  2. Atualizacao do snapshot no test
  3. Bump de versao (1.0.x se categoria 1 bug fix; 2.0.0 caso contrario)
- CHANGELOG.md entry obrigatorio listando dataset(s) afetados

### Deprecation policy

- `encode_table` / `decode_table` permanecem deprecated em v1.x (alias
  pra `encode(dict)` / `decode(text)`); REMOVIDOS em v2.0
- `DeprecationWarning` emit pra cada uso (ja' implementado)
- Outras APIs marcadas deprecated devem dar 1 minor antes de remover

### Migration v0.x → v1.0

Usuarios v0.6 nao precisam mudar nada se ja' usavam API publica:
```python
from tcf import encode, decode  # mesma API
```

Quem usava modulos internos (`tcf.encoder._encode_column`, `tcf.multi.
_encode_multi`) precisa migrar pra API publica.

### Migration v1.x → v2.0 (futuro)

Quando v2.0 vier (Layered Pipeline Fase 2 ou similar):
- Tag final v1.x mantida em pip
- Doc `docs/migration/v1-to-v2.md` enumera breaks
- Format `#TCF.7` lido por v2; gravacao pode opt-in `#TCF.6` legacy

## Consequences

### Positive

1. **Adocao**: paper/citacao referencia versao especifica
2. **Confianca**: usuarios sabem que codigo nao quebra em update minor
3. **Disciplina**: experimentos disruptivos forcam version bump major
   (pressao saudavel pra reduzir breaks)
4. **Suite regressao reforcada**: D1-D9 bytes frozen + D17a 322B
   INVARIANT vira contrato

### Negative

1. **Custo de manutencao**: mudancas em `src/tcf/` devem nao alterar
   bytes — exige cuidado extra
2. **Acumulacao de deprecated**: encode_table/decode_table presos ate'
   v2.0 (~1+ ano provavel)
3. **Pressao pra acumular features em v2**: tentacao de "esperar v2
   pra fazer X" se varios items pendentes

### Mitigations

- Para (1): suite test_regression_v1_baseline.py falha CI se mudou byte
- Para (2): listar deprecated em CHANGELOG, remover em batch em v2.0
- Para (3): RELEASE policy "no v2 antes de Q4/2026" — forca planejamento

## Out of scope (sub-ADRs futuros)

Itens identificados durante revisao mas adiados pra ADRs proprios:

- **ADR-0018 (futuro): Forward-compat decoder lenient mode** — decoder
  v1.x.y emite `warnings.warn("unknown marker, treating as literal")`
  em vez de raise. Facilita transicao v1→v2. Atualmente fora de escopo
  porque exige re-trabalho do parser pra distinguir "marker unknown"
  de "literal que comeca com `*`".
- **ADR-0019 (futuro): Security/emergency policy** — caminho explicito
  pra CVE no format que exija break em v1.x. Atualmente: politica
  "investigate first, propose ADR" caso ocorra.
- **ADR-0020 (futuro): Deprecation grace period** — minimo X meses
  entre primeiro `DeprecationWarning` e remocao. Padronizar (6 meses?).
  Atualmente: caso-a-caso.
- **ADR-0021 (futuro): Format v2 hint** — pre-anuncio do que cabe em
  `#TCF.7` (Layered Pipeline Fase 2 marker `*FALLBACK_X`, streaming
  chunks, possivel header binary opcional). Especulativo agora.

## Consequences

### Positive

1. **Adocao**: paper/citacao referencia versao especifica
2. **Confianca**: usuarios sabem que codigo nao quebra em update minor
3. **Disciplina**: experimentos disruptivos forcam version bump major
   (pressao saudavel pra reduzir breaks)
4. **Suite regressao reforcada**: D1-D9 bytes frozen + D17a 322B
   INVARIANT vira contrato
5. **Clareza de surface**: enumeracao explicita do que NAO e' API
   (#10) evita acidentes de usuarios importando internals

### Negative

1. **Custo de manutencao**: mudancas em `src/tcf/` devem nao alterar
   bytes — exige cuidado extra
2. **Acumulacao de deprecated**: encode_table/decode_table presos ate'
   v2.0 (~1+ ano provavel)
3. **Pressao pra acumular features em v2**: tentacao de "esperar v2
   pra fazer X" se varios items pendentes
4. **Lock-in de bug ambiguo**: bug "cosmetic byte diff" (categoria 2)
   exige 2.0.0 mesmo se trivial. Pode acumular dividas se varios
   detectados

### Mitigations

- Para (1): suite test_regression_v1_baseline.py falha CI se mudou byte
- Para (2): listar deprecated em CHANGELOG, remover em batch em v2.0
- Para (3): RELEASE policy "no v2 antes de Q4/2026" — forca planejamento
- Para (4): bug fix policy 3-categorias (Critico/Cosmetic/Perf) ajuda
  decidir; em duvida, sub-ADR especifico antes de bump

## Validation Plan

Antes de tag v1.0.0 (ordem de dependencia):

1. [ ] **Suite passing**: `pytest tests/test_regression_v1_baseline.py`
       passa 21/21 (gate de entrada — sem isso, nao continua)
2. [ ] **Public API test**: novo test em test_regression_v1_baseline.py
       asserta `set(tcf.__all__) == EXPECTED_API` (lista #5 acima)
3. [ ] **conftest.py**: `os.environ.setdefault("PYTHONHASHSEED", "0")`
       pra determinismo cross-platform
4. [ ] **Bump version**: `src/tcf/__init__.py` `__version__ = "1.0.0"`
       + `pyproject.toml` `version = "1.0.0"` + `requires-python = ">=3.10"`
5. [ ] **CHANGELOG.md**: secao `## 1.0.0 — 2026-MM-DD` listando
       "stable, frozen format #TCF.6, frozen API" + bug fix categoria
       (1) do `+-1,0`
6. [ ] **README.md**: badge versao + nota "stable since 1.0.0"
7. [ ] **CITATION.cff**: `version: 1.0.0` + `date-released: 2026-MM-DD`
8. [ ] **CI config**: workflow rodando `test_regression_v1_baseline.py`
       em toda PR, fail = block
9. [ ] **Git tag**: `git tag -a v1.0.0 -m "..."` + GitHub release com
       changelog
10. [ ] (Opcional) **DOI Zenodo**: arquivar versao pra cita academica

## Links

- [ADR-0001 — TCF format shebang](0001-tcf-format-shebang.md)
- [ADR-0014 — API unificada](0014-unified-api-side-outputs.md)
- [Suite regressao](../../tests/test_regression_v1_baseline.py)
- [METRICS baseline](../../experiments/lab/dirty/2026-05-27-baseline-consolidado/METRICS.md)
