# Welding plan — alg16 + M9 → src/tcf canonical motor

**Data**: 2026-05-17

> **Reorganizacao 2026-05-16**: pastas M-series referenciadas
> abaixo foram movidas pra `dirty/old/`. Paths no texto sao
> historicos; arquivos moram em `dirty/old/<path>`.


**Foco**: planejar saida do dirty lab. Migrar TCF-CORE (alg16) e
Compactacao composicional (M8.A) para `src/tcf/` como motor canonico
v0.6. Validar em **EXP-007** (clean experiment).

> **Cuidados criticos**:
> - NAO modificar alg16 (`online.py`) — copiar, nao tocar.
> - NAO modificar M8.A (canonico atual).
> - M9 (resultados validados em 9 datasets) e' a fonte de verdade
>   para regression: novo motor em src/ DEVE reproduzir M9 byte-a-byte.
> - Mover em **passos pequenos**, cada um verificavel.

## Inputs

| Componente | Fonte | LOC |
|---|---|---|
| alg16 (TCF-CORE) | `experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py` | 168 |
| M8.A composicional | `experiments/lab/dirty/old/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py` | 736 |
| M9 stress | `experiments/lab/dirty/old/2026-05-17-M9-stress-adversarial/` (9 datasets, RT 9/9 OK) | — |

## Estado atual

- `src/` vazio (`src/tcf/` movido para `old/tcf/` em 2026-05-17).
- `old/tcf/` = motor v0.5 (columnar/RLE/dict — acessorio).
- API conceitual (encode/decode/encode_columns/encode_rows) **estavel**;
  motor por baixo muda.

## Princípio

- API pública conceitualmente estável (encode, decode).
- Motor v0.6 (alg16 + composicional) **substitui** motor v0.5 mas
  preserva contrato encode→TCF text → decode→original.
- v0.6 inicialmente foca **1 coluna por dataset** (D1-D9 sao
  single-column). Multi-coluna virá num segundo encoder/organizador.

## Layout proposto src/tcf/

```
src/tcf/
  __init__.py             # API publica (encode, decode, EncodeConfig)
  core/
    __init__.py
    online.py             # alg16 (copia exata de M0)
    syntax_base.py        # interface Syntax
  composicional/
    __init__.py
    detector.py           # detector unificado (Phase B de M8.A)
    emit.py               # emit composicional (Phase C de M8.A)
    syntax.py             # wrapper M8.A
  encoder.py              # encode_string, encode_column (API public)
  decoder.py              # decode (API public)
```

Alternativa flat (se modules demais inflarem):
```
src/tcf/
  __init__.py
  alg16.py                # copia online.py
  composicional.py        # copia M8.A
  encoder.py
  decoder.py
```

## Fases (passos pequenos)

### Fase 1 — Esboco + decisao layout

- Decidir layout (modular vs flat).
- Criar `src/tcf/__init__.py` minimo.

**Checkpoint**: estrutura criada, vazia, sem quebrar nada.

### Fase 2 — Copy alg16

- Copiar `online.py` → `src/tcf/core/online.py` (ou flat).
- Adaptar imports (sem `sys.path.insert`).
- Smoke test: importar e tokenizar 1 string.

**Checkpoint**: `python -c "from tcf.core import online; ..."` funciona.

### Fase 3 — Copy M8.A

- Copiar `M8-A-detector-unificado/syntax.py` →
  `src/tcf/composicional/syntax.py` (ou splittar em detector.py + emit.py).
- Adaptar imports.
- Smoke test: encode/decode 1 dataset (D1) e comparar com M8.A.

**Checkpoint**: bytes identicos a M8.A em D1.

### Fase 4 — API público

- Definir `encode(values: list[str]) -> str` e `decode(text: str) -> list[str]`.
- Wrap alg16 + composicional internamente.
- Manter API conceitualmente igual a v0.5 (encode/decode) mas motor diferente.

**Checkpoint**: `tcf.encode(["abc", "def"])` produz TCF body string.

### Fase 5 — Smoke EXP-007

- Criar `experiments/lab/clean/EXP-007-prototipo-tcf-core/`.
- Rodar D1-D9 via API público.
- Comparar bytes com M9 (regression baseline).
- Confirmar RT 9/9 OK.

**Checkpoint**: EXP-007 reproduz M9 byte-a-byte (ou diferenca documentada).

### Fase 6 — Documentacao de uso

- Atualizar `src/tcf/__init__.py` docstring com exemplo.
- Possivelmente adaptar manual abstrato.

**Checkpoint**: usuario externo consegue rodar exemplo.

### Fase 7 — Multi-dataset (futuro)

D1-D9 sao single-column. API multi-column / multi-dataset e' fase
posterior (encoder/organizador que delega ao core por coluna).

## Riscos identificados

| Risco | Mitigacao |
|---|---|
| Quebrar alg16 ao adaptar imports | Copiar bit-exato; rodar diff |
| M8.A sem o `syntax_base.py` shared | Copiar ambos juntos |
| Trace/rede builders inflarem src/ | Manter como opcional (flag debug) |
| Tests v0.5 quebrarem definitivamente | Migrar tests pra v0.6 na Fase 6+ |
| Perder helper functions ao mover | Copiar TUDO de M8.A (helpers + main) |

## Nao-fazer (preservacao)

- ❌ Modificar arquivos do dirty lab (M0-M9) durante welding.
- ❌ Apagar `old/tcf/` (referencia v0.5).
- ❌ Re-implementar alg16 ou M8.A "limpo" — copia exata primeiro.
- ❌ Mudar API publica abruptamente (preservar encode/decode).

## Conexoes

- [[historia-dirty-lab.md]] — fonte da verdade
- [[roadmap-hipoteses.md]] — direcoes futuras (esta fase e' item #1)
- [[../../../../../old/tcf/__init__.py]] — API v0.5 para comparacao
