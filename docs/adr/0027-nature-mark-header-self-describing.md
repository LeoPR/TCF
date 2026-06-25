# 0027 — H-NAT-MARK-01: nature-id viaja no header (self-describing nature)

**Status**: accepted (MVP welded 2026-06-24)
**Date**: 2026-06-17 (proposed) · 2026-06-24 (accepted/welded)
**Deciders**: project owner
**Tags**: format, natures, self-describing, #TCF.8, DX

> **WELDED (MVP) 2026-06-24.** Parado em (A) de 2026-06-17 a 2026-06-24; o owner
> autorizou implementar a rota EXPLÍCITA. Implementado em `src/tcf` exatamente como
> desenhado abaixo (multi-col, 3 ids core, opt-in estrito, byte-neutro default-off).
> Commit do MVP + 9 testes (self-describing RT, byte-neutro, sem dupla-aplicação,
> unknown-id cru+warn, registry). **Correção de localização**: o diff abaixo cita
> `multi.py`, mas pós-P1 (2026-06-24) o código vive em `src/tcf/multi/core.py`
> (pacote). **Rota IMPLÍCITA avaliada e DESCARTADA** (insegura por construção: o
> reconhecimento `len+BASE94` pressupõe o spec, não o descobre → falso-positivo
> corromperia dado comum; ver [mapa de capacidade](../../experiments/lab/dirty/notas/specs-capacity-map.md)).
> Diferenças MVP vs design: id desconhecido surfaceia via `warnings.warn` (decode
> não tem `side_outputs`), não `SideOutputs.unknown_nature_ids`; precedência
> header-vence implementada em `decode()` (header resolve → aplica; usuário completa
> o resto). **Single-col TAMBÉM welded** (2026-06-24, ver §"Single-col" abaixo);
> lazy-view #TCF.8 segue PARKADO (fora do MVP).
>
> **FORMATO refinado por [ADR-0029](0029-version-format-identification-semi-implicit.md)**
> (discriminador de 1 char): o multi passou de `#TCF.8 M` + meta-line separada para
> `#TCF.8M<meta>` (sem espaço, meta INLINE na linha do shebang); single+spec =
> `#TCF.8 [nome]:spec`; novo `#TCF.8\n` = version-stamp. Os exemplos de meta-line
> abaixo (`!15=cpf,doc:cnpj`) refletem o design ORIGINAL; o conteúdo do meta é o mesmo,
> só migrou pra linha do shebang. Ver ADR-0029 §Realização pro formato vigente.

## Context and Problem Statement

As naturezas (CPF/CNPJ/IP — [ADR-0015](0015-natures-templated-checked-weld.md)) são
**pré-transform out-of-band**: `encode(col, nature=SPEC)` packa os valores antes do
pipeline, mas **o header não registra que houve nature**. Pra reverter, o `decode`
precisa receber o mesmo spec (`decode(text, nature=SPEC)`). Isso é fricção de DX
(o spec viaja por fora do blob) e impede interop (um terceiro que recebe o blob não
sabe que houve pré-tx).

Existe rota gadget zero-core: `natures_compiler/registry.py` (F1/F1.5) faz lookup
nome→spec (cpf/cnpj/ip semeados), então `decode(blob, nature_per_col={'col':
registry.get('cnpj')})` já funciona hoje — mas **o nome ainda não viaja no blob**.

## Decision Drivers

- **Critério registrado** (anti-incidente 2026-05-21): filtro novo só avança com
  **≥15% weighted em 2+ datasets reais**. Realidade: CNPJ nature = ganho relevante só
  em **receita** (1 real); CPF/IP só em sintéticos; ganho weighted na tabela some sob
  brotli. **F2 é infra/DX, não filtro** — o gate de bytes não se aplica diretamente,
  mas o **custo permanente** de um magic novo pesa contra um ganho de DX modesto.
- **Backward-compat inviolável**: #TCF.6/#TCF.7 lidos sem mudança; o caminho sem nature
  deve ficar **byte-idêntico** (D1-D9=1523B, D17a=303B).

## Decision Outcome (design, se/quando implementar)

Format change **#TCF.7 → #TCF.8** (= 0.8, NÃO v2.0 — [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md)),
**opt-in estrito**: #TCF.8 emitido **SSE** alguma coluna tem nature; senão #TCF.7
byte-idêntico.

### Header tag
Sufixo **`:`** no nome da coluna no meta-line (não `^`, não `#`). `:` é familiar
(key:value), não colide com marcadores de modo `!@%` (PREFIXO de size) nem com
reservados HCC `~`/`,`. O validador de nome em `multi.py` (que já proíbe `,`/`=`)
passa a proibir `:` também.

- **ANTES** (#TCF.7, `cpf` raw + `doc` com CNPJ, sem trace): `!15=cpf,doc`
- **DEPOIS** (#TCF.8): `!15=cpf,doc:cnpj` (o `:cnpj` no fim do nome)
- Parse: modo-prefix (`!@%`) → `=` (size/name) → `:` no name (name/nature-id).

### Resolução no decode — CORE-ONLY
Lookup em dict fixo `{'cpf':SPEC_CPF,'cnpj':SPEC_CNPJ,'ip':SPEC_IP}` em
`src/tcf/natures/__init__.py`. **Zero eval, zero código vindo do header.** Rejeitadas:
DSL-no-header (infla header + vetor de injeção) e registry-compartilhado (frágil em
versionamento/terceiros). **ID desconhecido** → fallback explícito: retorna valor CRU
(sem reverter pré-tx) + `SideOutputs.unknown_nature_ids` (NÃO KeyError, NÃO silencioso)
→ forward-compat. Usuário completa com `nature_per_col` manual (header takes precedence
só pros 3 ids core). Terceiros continuam out-of-band via registry gadget.

## Scope / diff em src/tcf (se implementar)

- `multi.py`: `MAGIC_MULTI_V3 = b'#TCF.8 M'`; `_encode_multi(nature_ids=...)`; meta-line
  appenda `:id`; magic sse `bool(nature_ids)`; parser extrai `:`; decode resolve+aplica,
  id desconhecido → cru+flag; validador proíbe `:` em nome.
- `encoder.py`: ramo dict constrói `nature_ids = {name: spec.name}` (só a STRING).
- `decoder.py`: dispatch aceita `#TCF.8 M`.
- `natures/__init__.py`: `SPEC_REGISTRY` + `_resolve_nature_id(id)->spec|None` (aditivo).
- `side_outputs.py`: `multi_info.nature_cols` + `unknown_nature_ids`.
- `scripts/tcf_lazy/lazy.py` (gadget, fora de src/tcf): parser de `:id` + aceitar #TCF.8.

## Compat + GATE

- #TCF.6 (congelado [ADR-0017](0017-format-spec-v1-frozen.md)) e #TCF.7 lidos sem
  mudança. #TCF.7 sem nature = **bytes idênticos** (D1-D9=1523B, D17a=303B).
- **GATE**: F2 toca encode/decode core → `tests/test_real_world_snapshots.py` verde +
  D1-D9 + D17a + RT com-nature. Weld só após os DOIS suites verdes.

## Testes (se implementar)

`test_nature_mark_roundtrip` (encode com nature → decode SEM nature recupera);
`test_nature_mark_backward_compat` (GATE byte-idêntico); `test_nature_mark_unknown_id`
(forward-compat, cru+flag); `test_nature_mark_user_override`; `test_lazy_tcf8`.

## Pros and Cons

**Pros**: self-describing (decode reconhece a nature sozinho) + interop; opt-in,
default-off, zero-regressão por construção; design fechado e core-only (sem eval).

**Cons / por que parado**: ganho de compressão das natures não bate o gate
(≥15%/2 reais); a DX já tem rota zero-core (registry gadget) → o delta real é só "nome
viaja no blob"; **custo permanente** de um magic `#TCF.8` que decoder/lazy/terceiros
carregam pra sempre. Desproporção ganho×custo → **parado em (A)**.

## Single-col — WELDED (2026-06-24)

> Atualização: o park original (abaixo) foi resolvido. O owner notou que single-col
> = multi-col com 1 coluna (header implícito) e que um shebang **opt-in** (só quando
> há nature) preserva o byte-canonical de todo single-col SEM spec.

**Formato** (header numa LINHA SÓ, junto ao shebang como o flag `M` — owner
2026-06-24): `#TCF.8 [nome]:spec_id\n<body>`. A **ausência do flag `M`** distingue
single (`#TCF.8 <...>`) de multi (`#TCF.8 M`) — o decode retorna `list` (não
`dict`), preservando `decode(encode(list)) == list`. O `[nome]:spec_id` fica na
própria linha do shebang (sem linha extra; o espaço troca o `\n`, mesmo custo
~12B). **nome OPCIONAL** (só rótulo de acompanhamento; descartado no decode;
vazio = `:cpf`).

- `encode(list, nature=SPEC, name=None)`: shebang emitido SSE `nature` passado.
  `MAGIC_SINGLE_V3 = b"#TCF.8"`. Valida `name` sem `:`/`\n`.
- `decode`: dispatch do multi por **match EXATO** de `line1` (`line1 in (magics)`,
  não startswith) — necessário pra um `name` começando em `M` (`#TCF.8 Meu:cpf`)
  não colidir com `#TCF.8 M`. Single = `line1.startswith("#TCF.8 ")`. Resolve via
  `_resolve_nature_id` (core-only); precedência header-vence; id desconhecido →
  cru + `warnings.warn`.

**byte-neutro**: single-col SEM spec = body puro byte-idêntico (D1-D9=1523B intacto);
custo ~12B de header só no opt-in. Welded com 9 testes (test-first).

**Park original** (resolvido): "single-col não tem header; embutir shebang quebraria
o byte-canonical de todo single-col" — verdadeiro só se o shebang fosse SEMPRE
emitido; com opt-in (só quando há nature), o caminho sem-spec fica intacto.

## Relation to other ADRs

- [ADR-0015](0015-natures-templated-checked-weld.md) (natures): F2 torna a nature
  self-describing; hoje é out-of-band.
- [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md) (versioning): #TCF.8 = 0.8,
  marcador de dev, NÃO v2.0; baselines re-pináveis (mas aqui NÃO mudam — default-off).
- [ADR-0017](0017-format-spec-v1-frozen.md) (#TCF.6 frozen): inalterado.
- **H-NAT-MARK-02** (registry modular/plugins) e **H-CODEBOOK-01** (outer-dict
  versionado): concerns separados; ADR-0027 é só formato/parsing do nature-id core.

## Links

- [Design note + revisão crítica](../../experiments/lab/dirty/notas/f2-nature-mark-header-design.md)
- [Pesquisa CEP/outer-dict](../../experiments/lab/dirty/notas/cep-outer-dict-codebook-pesquisa.md)
