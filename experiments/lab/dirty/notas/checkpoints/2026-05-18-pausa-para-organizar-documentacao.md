# Checkpoint — Pausa para organizar documentacao

**Data**: 2026-05-18
**Tipo**: pausa estrategica
**Motivo**: descoberto que documentacao/memoria nao reflete infra
existente; pausa pra reorganizar antes de continuar EXP-012.

> **PRECISO LEMBRAR DESSA CONVERSA NESSE PONTO**. Este arquivo e' o
> ponto exato pra retomada. Quando user disser "vamos voltar para o
> checkpoint", este e' o doc a abrir.

## O que estavamos fazendo (CONTEXTO PRECISO)

**Lab ativo**: `experiments/lab/clean/EXP-011-multi-column-basic/`
(multi-column basico, header `#TCF.6 M` uniformizado, RT 20/20 OK
em D17a, -46% vs raw).

**Proximo experimento planejado**: **EXP-012 — real-world test**
(Adult Census ou TPC-H).

**Decisao tomada**: usar infra existente em vez de
download/synthesize. Concretamente:

```python
# scripts/dataset_reader.py + scripts/shaper/ ja' prontos.
# Z:/tcf-data/interim/{adult-census,tpch-sf001}.db ja' existem.

from dataset_reader import DatasetReader
from shaper import Shaper, ShapeRequest

req = ShapeRequest(
    dataset="adult-census",
    volume=1000,
    order="natural",
    seed=42,
)
result = Shaper().apply(req)
table = result.tables["adult"]
cols = {k: [str(row[k]) for row in table] for k in table[0].keys()}

# Aplica EXP-011 pipeline
from multi_col import encode_table, decode_table
tcf_text, info = encode_table(cols)
```

**Confirmacao pendente do user**: "Confirma que sigo com essa
abordagem?" — antes de codar EXP-012.

## Por que pausamos

User identificou problema sistemico:
- Tentei baixar dataset externo quando infra estava pronta
- Demonstra que **documentacao/memoria nao tem visibilidade**
- Coisas obsoletas nao marcadas; coisas novas esquecidas
- Desviar do assunto = catastrofe no desenvolvimento

User pediu:
1. Salvar este checkpoint (este doc)
2. Pesquisar literatura/boas praticas modernas:
   - Documentacao organizada cientificamente
   - Memoria de IA / chats generativos em ferramentas como VSCode
   - Big tech approaches (Microsoft, Google, GitHub, etc.)
3. Auditar docs existentes
4. Propor sistema organizado
5. Implementar
6. Retomar EXP-012 deste checkpoint

## O que NAO mudar enquanto pausamos

- src/tcf/ intocado (mesma garantia historica)
- EXP-010, EXP-011 ja' funcionais — nao mexer
- Pacote 1 (delta-aware) fechado — nao revisar
- Infra existente (scripts/shaper, dataset_reader, _paths)
  — nao tocar, ja' funcional

## O que ARRUMAR durante a pausa

- Sistema de documentacao
- Memoria persistente (MEMORY.md + entries)
- Discoverability (como achar coisas)
- Marcacao de obsoletos
- Indices/registros centrais

## Como retomar deste checkpoint

1. Abrir este arquivo (`2026-05-18-pausa-para-organizar-documentacao.md`)
2. Ir pra "O que estavamos fazendo" acima
3. Executar a confirmacao pendente: criar EXP-012 com shaper
4. Continuar normalmente

## Status da pausa (atualizado 2026-05-18 fim do dia)

**Reorganizacao COMPLETA**. Sistema implementado:
- Fase 1: `CLAUDE.md`, `MAP.md`, hooks `.claude/`
- Fase 2: 5 ADRs (`docs/adr/`), `docs/vocabulary.md`, YAML
  frontmatter em READMEs ativos, stale markers
- Fase 3: cross-links "See also", `scripts/index.py` + `INDEX.md`,
  `docs/how-to/audit-memorias-e-documentacao.md`

Detalhes em [`../diario/2026-05-18.md`](../diario/2026-05-18.md).

**Proxima sessao deve**:
1. Confirmar leitura do `CLAUDE.md` raiz (sessao start hook injeta)
2. Retomar EXP-012 conforme "O que estavamos fazendo" deste arquivo
3. Criar `experiments/lab/clean/EXP-012-real-world-shaper/` e usar:
   ```python
   from dataset_reader import DatasetReader
   from shaper import Shaper, ShapeRequest
   ```

**Status do checkpoint**: still ACTIVE (EXP-012 pendente).
Marcar `resolved` so' apos EXP-012 ser concluido.
