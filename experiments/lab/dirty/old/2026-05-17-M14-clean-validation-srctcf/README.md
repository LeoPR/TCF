# M14 — Clean validation: src/tcf como unica fonte

**Data**: 2026-05-17
**Estado**: foi (fechado, contra-prova validou)
**Welding step**: 4 (contra-prova final)
**Foco**: provar que `from tcf import encode, decode` funciona
APENAS via `src/tcf/`, apos cleanup das libs temporarias de
welding em M10/M11.

## Contexto

Apos M13 (welding step 3) validar que `src/tcf` tem encode/decode
formalmente funcionando, user pediu uma **contra-prova absoluta**:
remover as libs temporarias de encode/decode do dirty lab (welding
scaffolding) e RE-EXECUTAR M13 como M14.

Se M14 continua produzindo bytes byte-identicos, prova que src/tcf
e' realmente a unica fonte — sem resquicio de import vindo de algum
modulo welding-scaffolding deixado no dirty.

## Cleanup precedente (commit `8aad4fd`)

Removido do dirty lab:
- `M10/online.py`
- `M10/syntax_base.py`
- `M10/M8-A-baseline/syntax.py`
- `M11/syntax_base.py`
- `M11/M8-A-baseline/syntax.py`

Efeito colateral: M10 e M11 nao sao mais reexecutaveis individualmente
(eram welding scaffolding). Resultados em `debug/`, `decoded/`,
`output/`, `redes/`, `detector_trace/` permanecem como registro
historico do byte-canonico.

**Preservado**:
- `M0/online.py` (alg16 fonte original)
- `2026-05-16-M8/M8-A-detector-unificado/syntax.py` (M8.A canonical)
- M4-M9 snapshots (registro experimental fechado)
- M12, M13 (ja' nao tinham copias locais)
- `src/tcf/` inteiro (canonico)

## Mudanca vs M13

Identico em logica. Apenas:
- output dir: `M13-tcf-api/` → `M14-tcf-clean/`
- docstring: descreve contra-prova
- mensagens de print

Nenhuma mudanca no codigo de encode/decode (vem de `src/tcf` via API
publica).

## Resultado

RT 9/9 OK. Bytes byte-a-byte identicos a M13:

```
diff -r M13/M13-tcf-api/output M14/M14-tcf-clean/output
  → vazio, exit 0
```

| Dataset | M13 | M14 | diff |
|---|---:|---:|---:|
| D1 | 118 | 118 | 0 |
| D2 | 166 | 166 | 0 |
| D3 | 177 | 177 | 0 |
| D4 | 113 | 113 | 0 |
| D5 | 281 | 281 | 0 |
| D6 | 287 | 287 | 0 |
| D7 | 215 | 215 | 0 |
| D8 | 100 | 100 | 0 |
| D9 | 158 | 158 | 0 |
| **Total** | **1615** | **1615** | **0** |

Total raw 2981, ratio 54.2%.

## Significado

**Cadeia byte-identica final**: M0 alg16 → M8.A composicional →
M9 → M10 → M11 → M12 → M13 → **M14 (clean validation)**.

**src/tcf/ formalmente certificado**:
- Sem dependencia de modulos welding-scaffolding
- Importavel diretamente via `from tcf import encode, decode`
- Reproduzem-se os bytes canonicos do dirty (validados em 9 datasets,
  ratio 54.2%, RT 9/9 OK)

**Dirty lab e' agora backup canonico**:
- M0-M9: registro experimental do algoritmo
- M10-M13: registro do welding (sem libs locais a partir do cleanup)
- M14: certificacao do estado final

Pronto para:
1. Reorganizar documentacao com seguranca (src/tcf consolidado)
2. Criar EXP-007 em `experiments/lab/clean/` como primeiro
   experimento clean v0.6
3. Eventualmente liberar/reorganizar dirty lab

## Cuidados (memory flow)

- ✋ NAO modificou alg16 original (`M0/online.py`)
- ✋ NAO modificou M8.A original (`2026-05-16-M8/.../syntax.py`)
- ✋ NAO modificou outros macros (M1-M9, M12, M13)
- ✋ NAO modificou `src/tcf/`
- ➕ Adicionou M14 (clean validation)
- (Cleanup precedente em commit `8aad4fd` — independente)

## Conexoes

- `../notas/welding-plan.md` — plano completo
- `../2026-05-17-M13-welding-step3-api-publica/` — checkpoint anterior
- Commit de cleanup precedente: `8aad4fd`
