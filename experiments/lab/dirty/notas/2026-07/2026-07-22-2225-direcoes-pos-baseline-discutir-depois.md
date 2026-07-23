# Direções registradas 2026-07-22 (pós-baseline) — DISCUTIR DEPOIS [dispositivo→registro]

Três direções que o owner levantou ao pedir a lista de funcionalidades do `.8`.
**Nada a executar agora** — registro pra não ficar só na conversa; discussão adiada.

## 1. Specs precisam de desacoplamento mais duro + linguagem própria

Os specs (naturezas: CPF/CNPJ/IP) ainda **não** passaram por um processo de
desacoplamento suficientemente rígido, e devem ter **linguagem/DSL própria** (não
ficar acoplados ao pipeline como estão). Relaciona:
[T-SPEC-STATUS-08](../../../../../tickets/T-SPEC-STATUS-08.md) ·
[T-SPEC-DEEPDIVE-08](../../../../../tickets/T-SPEC-DEEPDIVE-08.md) ·
[T-OPT-INFERENCE](../../../../../tickets/T-OPT-INFERENCE.md) (specs induzidas) ·
o "compilador DSL/registry" que já existe em `scripts/` mas não é registry publicável do core.
→ candidato a trabalho de `1.0` (contrato/linguagem de formato).

## 2. `view` precisa ser verificada pra avaliar performance

O baseline de perf de hoje mediu só **ENCODE** (entrada→wire). A camada `view()`
(lazy read-only, L1-L4) **não foi medida** — decode/query tem perfil próprio
(decode é serial; coluna `tcf` entrelaçada cai em materialização total). Precisa
de caracterização de performance própria antes de qualquer claim.
Relaciona: `src/tcf/view.py` · [T-DOC-LAZY-REFERENCE](../../../../../tickets/T-DOC-LAZY-REFERENCE.md) ·
H-QUERY-04 (`.9`). → estender o `bench_perf` pra cobrir decode/view.

## 3. CNPJ — revisão SÉRIA (o caveat do closeout pode estar errado)

**O owner suspeita que o spec CNPJ está mal-implementado, além da forma de conduzir
a compressão.** Convicção: **sempre há ganho pro spec, mesmo em caso real** — a
`forma` está incorreta, embora **compressão e RT estejam corretos**. Olhou os labs
e diz que **não estão corretos**.

Isto **CONTRADIZ diretamente** o achado F4 que hoje é caveat obrigatório do F6/release:
> "nature CNPJ PIORA em receita REAL (+7339B, split→raw), só ajuda no sintético"
> (T-QA-8 §2d / T-REL-08-CLOSEOUT / T-SPEC-STATUS-08 Opção A).

Se o owner estiver certo, o caveat é artefato de lab/spec mal-conduzido, não
propriedade real → **o caveat do release precisa ser reavaliado antes de ir pro
README (F6)**. Ação futura: re-revisar o lab de natures (a `forma` da compressão
CNPJ), com a suspeita de que o ganho real existe e o lab o mascarou.
Relaciona: `src/tcf/natures/templated_checked.py` · ADR-0015 ·
[T-SPEC-STATUS-08](../../../../../tickets/T-SPEC-STATUS-08.md) ·
labs de natures (welded/`2026-05-24-cpf-templated-checked` em `old/`) ·
gate real-world [T-DATA-2-RECEITA-CNPJ](../../../../../tickets/T-DATA-2-RECEITA-CNPJ.md).

> ⚠️ Enquanto não resolvido, o número do F4 (CNPJ piora em real) fica **sob
> suspeita** — não fechar o README do `.8` afirmando isso como propriedade sem a
> revisão.

## 4. `encode_hierarchical` exposto é ERRO de API (viola API unificada)

O owner apontou: **não deveria existir `encode_hierarchical` público — só `encode`.**
Hoje `src/tcf/__init__.py` exporta `encode_hierarchical` em `__all__`, e o `encode`
só aceita **flat** (`list[str]` | `dict[str, list[str]]`), sem rotear aninhado — então
o dev é **forçado** a chamar a função separada. Isso viola a API unificada (ADR-0014:
"`encode(list|dict)`") e é **assimétrico** com o `decode`, que JÁ auto-roteia pelo magic
(`#TCF.8M`/`#TCF.8H`/órfão).

**Correção esperada**: `encode` detecta input aninhado (dataset/dict-de-dicts/
list-de-dicts) e roteia pro `#TCF.8H` internamente; `encode_hierarchical` sai do
`__all__` (no máximo vira interno). Toca `src/tcf` (dispatch do encoder) → precisa de
aprovação. Candidato a fechar no F6/pré-1.0 (a superfície pública do dev deve ser só
`encode`/`decode` + `view` + `SideOutputs` + specs).
Relaciona: `src/tcf/encoder.py`, `src/tcf/hierarchical.py`, ADR-0014,
[T-CODE-TCF8H-WELD](../../../../../tickets/T-CODE-TCF8H-WELD.md).
