# F2 — H-NAT-MARK-01: nature-id viaja no header (#TCF.8) [design, pré-decisão]

**Data**: 2026-06-17 · design (NÃO implementa). Origem: owner "f2".
**Estado**: HISTÓRICO (faxina 2026-06-21) — design fechado, **decisão tomada: NÃO
implementar agora** (opção A). Registrada em **ADR-0027 (proposed)** e **deferida pro
0.9** ([`v08-plano-etapas.md`](v08-plano-etapas.md)). **Nada tocado em `src/tcf/`**.
Revisitar só com um 2º nature real demandando self-describe. Fica como o design de referência.

## O que F2 resolve
Hoje a nature é **pré-transform out-of-band** (ADR-0015): `encode(col, nature=SPEC)`
packa antes do pipeline, mas **o header não registra que houve nature**. Pra reverter,
o `decode` precisa receber o spec de novo (`decode(text, nature=SPEC)`). F2 = fazer o
**nature-id viajar no blob** pra o decode reconhecer a nature sozinho (self-describing).
É **format change #TCF.7 → #TCF.8** e **toca `src/tcf` core**.

## Revisão crítica honesta — vale agora?
**Não vale weldar agora como format change.** Razões:
- **Critério não batido**: o gate registrado (≥15% weighted em 2+ datasets reais) só
  bate pra **CNPJ em receita** (1 real). CPF/IP só em sintéticos. O ganho weighted na
  tabela (adult 14.5%, receita 7.1%, tpch 3.4%, beijing 1.3%) **some sob brotli**.
- **F2 é infra/DX, não filtro novo** — o argumento "o gate de bytes não se aplica a
  infra" é válido em tese, mas pesa pouco contra o **custo permanente**: um magic novo
  `#TCF.8` que decoder + lazy + qualquer terceiro carrega **pra sempre**.
- **A DX já tem rota zero-core**: o gadget `natures_compiler/registry.py` já faz
  lookup nome→spec (cpf/cnpj/ip semeados). `decode(blob, nature_per_col={'col':
  registry.get('cnpj')})` **já funciona hoje**. A self-description só adiciona o NOME
  viajar NO blob — e o nome poderia viajar como metadado lateral (sidecar/SideOutputs/
  convenção de nome) **sem bump de formato**.

→ **Recomendação**: aprovar o DESIGN (este doc + ADR-0027 em `proposed`, não
`accepted`), e **não implementar no core** até (a) surgir um 2º nature real com ganho,
ou (b) o owner decidir que a self-description-no-blob vale o bump permanente só por DX.

## Design do header (se implementar)
Tag = **sufixo `:` no nome da coluna** no meta-line (NÃO `^`, NÃO `#`). Justificativa:
`:` é familiar (key:value), não colide com marcadores de modo `!@%` (que são PREFIXO de
size) nem com reservados HCC `~`/`,`; o validador de nome em `multi.py` já proíbe `,` e
`=` — basta adicionar `:`.

- **ANTES** (#TCF.7, coluna `cpf` raw + `doc` com CNPJ pré-tx, sem trace de nature):
  `!15=cpf,doc`  ← a info de que `doc` teve CNPJ **não existe** no header.
- **DEPOIS** (#TCF.8): `!15=cpf,doc:cnpj`  ← o `:cnpj` no fim do nome.
- Parse: split por modo-prefix (`!@%`) → `=` (size/name) → `:` no name (name/nature-id).
- Magic linha1: `#TCF.8 M` emitido **SSE** alguma coluna tem nature; senão `#TCF.7 M`
  **byte-idêntico** ao atual (opt-in estrito, default-off).

## Resolução no decode (se implementar)
**CORE-ONLY** é a única resolução aceitável: lookup em dict fixo
`{'cpf':SPEC_CPF,'cnpj':SPEC_CNPJ,'ip':SPEC_IP}` em `src/tcf/natures/__init__.py`.
**Zero eval, zero código vindo do header.** Rejeitadas: DSL-no-header (infla header +
vetor de injeção) e registry-compartilhado (frágil em terceiros/versionamento).
**ID desconhecido** → **fallback explícito**: retorna valor CRU (sem reverter pré-tx) +
sinaliza via `SideOutputs.unknown_nature_ids` (NÃO KeyError, NÃO silencioso) →
forward-compat (um #TCF.8 com spec futuro 'cep' continua legível; usuário completa com
`nature_per_col` manual).

## Diff exato em src/tcf (se implementar)
- `multi.py`: `MAGIC_MULTI_V3 = b'#TCF.8 M'`; `_encode_multi` ganha `nature_ids`; meta-line
  appenda `:id`; magic emitido sse `bool(nature_ids)`; parser de pares extrai `:`; loop de
  decode resolve+aplica, id desconhecido → cru+flag; validador proíbe `:` em nome.
- `encoder.py`: ramo dict constrói `nature_ids = {name: spec.name}` (só a STRING).
- `decoder.py`: dispatch aceita `#TCF.8 M`.
- `natures/__init__.py`: `SPEC_REGISTRY` + `_resolve_nature_id(id)->spec|None` (aditivo).
- `side_outputs.py`: `multi_info.nature_cols` + `unknown_nature_ids`.
- `scripts/tcf_lazy/lazy.py` (gadget, QUEBRA se não tocado): parser de `:id` + aceitar #TCF.8.

## Compat + GATE
- **Inviolável**: #TCF.6/#TCF.7 lidos sem mudança; #TCF.7 sem nature = **bytes idênticos**
  (D1-D9=1523B, D17a=303B). Bump pra #TCF.8 é opt-in estrito (só com nature).
- **GATE**: F2 toca encode/decode core → `tests/test_real_world_snapshots.py` verde +
  D1-D9 + D17a + RT com-nature. Weld só após os DOIS suites verdes.

## Testes novos
`test_nature_mark_roundtrip` (encode com nature → decode SEM nature recupera);
`test_nature_mark_backward_compat` (GATE: #TCF.7 byte-idêntico); `test_nature_mark_unknown_id`
(forward-compat, cru+flag); `test_nature_mark_user_override`; `test_lazy_tcf8`.

## ADR
**ADR-0027** — "H-NAT-MARK-01: Nature Identifier viaja no header TCF". Estado inicial
**`proposed`** (não accepted/welded até aprovação+gate). #TCF.8 = 0.8 (NÃO v2.0, ADR-0024).
Single-col: **PARK explícito** (sem header; shebang em single-col quebraria byte-canonical
de tudo). Relação com H-NAT-MARK-02 (registry modular): ADR-0027 é só formato/parsing.

## Decisão pendente (owner)
- **(A)** NÃO implementar agora — manter design + ADR-0027 `proposed`; revisitar com 2º nature real. *(recomendado)*
- **(B)** rota BARATA — nome viaja como metadado lateral/convenção, sem bump de formato (captura a DX sem #TCF.8). *(recomendado)*
- **(C)** aprovar o bump #TCF.8 agora (CORE-ONLY, opt-in, default-off, GATE preservando D1-D9/D17a) assumindo que a self-description-no-blob vale o custo permanente só por DX/interop.

Fonte: workflow `_wf_f2_design.js` (task w34x1u4fl, 3 lentes + síntese).
