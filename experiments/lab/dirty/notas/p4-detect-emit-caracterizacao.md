# P4 — Caracterização detect/emit do HCC (foco-2, read-only)

**Data**: 2026-06-24. **Origem**: foco-2 (clareza/minimalismo do CORE pro port C/Rust).
**Método**: workflow read-only (8 agentes — 4 leitores + síntese + 3 críticos
adversariais: byte-risk, espelho-pyx, clareza-de-port). Caracterização ANTES de
tocar `src/tcf/`. Companheiro de [docs/algorithms/core-data-model.md](../../../../docs/algorithms/core-data-model.md) (P3).

> **Status**: caracterizada; **Onda 1 EXECUTADA** (2026-06-24, owner aprovou só ela).
> Commits: `4cd7283` (S0+S2+S3 docs), `91e3cf9` (S4 `_EmitState`), `0be4649` (S5
> `current_id` int), `229d873` (S6 ref_seqs trace-only). Todos byte-neutros (31 gates
> byte-canonical + RT + suite 375 verdes). Detector e `.pyx` intocados na Onda 1.
>
> **Onda 2**: **S7 EXECUTADO** (commit `_emit_runs`, equivalência verificada 200k
> casos + GATE; só emit/trace, não toca detector/.pyx). **S8 PENDENTE de avaliação
> futura** (owner: "depois fazemos o S8") — risco ALTO (função de custo do detector,
> consumida pelo `.pyx`), gated por [T-CI-3](../../../../tickets/T-CI-3-pyx-compiled-byte-gate.md).
> **S1 NÃO executado** (não tocar `.pyx` sem gate). Buraco de gate-pyx + dimensão de
> distribuição (otimização tem que chegar ao usuário) → [T-CI-3](../../../../tickets/T-CI-3-pyx-compiled-byte-gate.md).

## O acoplamento hoje (caracterização)

O miolo é `M8AVirtualRefsSyntax` em `composicional/syntax.py`. `encode()` (567-580)
fixa a ordem **tokenize → detect → emit → trace → join**.

- **DETECT** (`_detect_compositions` 232-384): acha sub-tuplas de refs repetidas,
  net `(R-1)*(baseline-len_id)`, seleção gulosa, prune ADR-0019; substitui in-place
  em `pieces_per_line`. Retorna `alias_to_sub` (**único dict de saída byte-relevante**)
  + `iter_traces` (só debug).
- **EMIT** (`_emit_body` 413 + `_emit_ref_run` 492 + `_emit_alias` 517): lê
  `pieces_per_line` mutado + `alias_to_sub`, gera body textual, aloca **id final por
  ordem de body** (single-pass).
- **Canal de acoplamento**: inteiramente por (a) mutação in-place de `pieces_per_line`
  e (b) o dict `alias_to_sub`. As assinaturas (`_detect_compositions` e o retorno de
  `_emit_body`) são **contrato congelado** com `detect.pyx` e com `build_trace`/`encode`.

**O que atrapalha um port (consenso dos 3 críticos)**:
1. **EMIT** carrega o pior: dict `state` opaco mutado por referência (mistura
   read-only `alias_to_sub`, read-write `current_id`/`prov_to_final`/`alias_to_final`,
   debug `ref_seqs`); `current_id=[0]` (lista-de-1 = cell de int mutável); closure
   recursiva `expand()`. **Alto ganho de clareza, baixo risco de byte, não toca .pyx.**
2. **DETECT** funde no mesmo loop quente o running-max byte-load-bearing
   (`best/best_net`, `>` estrito = tie-break first-wins na ordem do Counter), o append
   em `candidates` (só trace) e o prune. Separar = marginal (a assinatura com
   `iter_traces` não muda) **e toca o .pyx**.
3. **Buraco sistêmico de gate**: NENHUM teste exercita o `detect.pyx` COMPILADO
   (ambiente `accel=False`; grep em tests/ por accelerated/_core/pyd = 0 hits). ADR-0020
   exige byte-equivalência .py↔.pyx mas a suíte nunca valida o caminho compilado →
   qualquer edição no .pyx passa os gates locais e pode quebrar silenciosamente onde
   a extensão estiver compilada. **Independe do P4, mas o P4 tornou visível.**

## Plano revisado (incorpora os 3 críticos)

Reordenado vs o plano cru: EMIT-only de alto-valor/baixo-risco PRIMEIRO; detector/.pyx
e fusões DRY por último ou fora.

### Onda 1 — EMIT-only + docs (sem .pyx, ataca o eixo real, byte-neutro)

- **S0 (NOVO, do crítico port-clarity)** — docstring/tipo da **tagged-union** dos
  pieces/refs (`('lit',text,id)` | `('refs',[ids])`; sinal `>0`=atom `<0`=-alias;
  `None`=linha repetida) em `_tokenize_pieces` + `_detect_compositions`. **Risco zero**
  (só .py, sem espelho .pyx). Maior razão clareza/risco — é o que vira `enum` no port.
- **S2** — nomear a precondição de `_emit_alias.expand`. ⚠️ formular como **"inner
  NÃO-resolvido em position 0"** (não "todo inner em position 0"): inner já em
  `alias_to_final` pode estar em qualquer posição (538-540); só o não-resolvido recursa
  em pos 0 (542-545). Assert sob `__debug__`, zero efeito colateral.
- **S3** — co-localizar as 4 condições de separador como tabela documentada (comment-only):
  lit→lit=`*`; refs→lit-começa-`,`/`~`=`*` (ADR-0007); refs→refs=`,`; lit-term-digit→refs=`*`.
- **S4** — trocar dict `state` por struct nomeado `EmitState`. ⚠️ **OBRIGATÓRIO** uma
  **instância mutável compartilhada por referência** (dataclass com campos dict/list
  referenciados) — NUNCA namedtuple/frozen/desempacotar (a closure `expand` fecha sobre
  a MESMA instância; cópia por valor quebra ids finais). Preservar a tupla de retorno
  `(body, prov_to_final, alias_to_final, ref_seqs)`.
- **S5** — `current_id` → contador explícito. ⚠️ preservar a semântica **read-then-incr**
  por sítio: @465-466 incrementa-então-lê (id=valor novo); @553-554 lê-então-incrementa
  (base=valor antigo, depois +=K-1, usado em base+idx@560); @507 incrementa-em-bloco.
  Fazer junto/após S4.
- **S6** — `ref_seq`/`ref_seqs` como TRACE-ONLY **in-place** (versão mínima: só rotular).
  ⚠️ NÃO dá pra "extrair" de verdade (atravessa a fronteira `encode`); flag (se houver)
  default **LIGADO** pra preservar `SideOutputs.hcc_trace`/`.hcc_rede`; manter `append([])`
  no ramo `is_rep` (alinhamento posicional li↔ref_seqs).

### Onda 2 — opcional, DRY (≠ redução de acoplamento), risco médio

- **S7** — fundir `_emit_refs_range` (`,`) e `_emit_composition` (`~`). ⚠️ diferem em
  **DOIS eixos** (granularidade do que vira "parte" para run<3 + join externo), não só
  o caractere. Parametrizar AMBOS os separadores ou só compartilhar `_runs_pos`+regra
  range. Gate real-world OBRIGATÓRIO. **Só fazer se ficar obviamente mais simples.**
- **S8** — `_estimate_baseline_chars`: **reclassificado risco ALTO** (não médio) ou
  **non-goal**. A estimativa roda sobre **prov-ids** (pré-emit, virtual=`'9'*n_est`); o
  emit sobre **final-ids** (pós-alloc) — espaços de id diferentes por design. Passar o
  sub MIXTO por `_runs_pos` (assume todos positivos) quebra. Consolidar SÓ um helper de
  **formatação pura** (ints→ranges), nunca o cálculo de consecutividade. Melhor servido
  por um **teste de propriedade `estimativa==emit`** que por fusão estrutural.

### Bloqueado / fora desta rodada

- **S1** (extrair trace do DETECT) — **NÃO tocar o .pyx por um comentário**. A coleta
  de trace não sai sem mudar a assinatura (proibido), então é só re-comentar o loop
  quente = ganho marginal + risco de drift num arquivo não-testado. Se um dia for: ou
  .py-only + TODO de sync no .pyx, ou exige gate com .pyx COMPILADO (que não existe).

## Cross-cutting (qualquer step)

- **HCCSeqRLE** (`hcc_seqrle.py:266`) consome `_emit_body` via `super().encode()` +
  fatia `[:-1]` do `\n`-join. S4/S6 devem preservar a tupla de retorno + o formato join.
- Para steps risco médio/alto (S7/S8): **snapshot byte-a-byte do .tcf real** (diff
  antes/depois), não só a contagem agregada — pega mudança que preserva o total mas
  altera distribuição.
- Cobertura de **virtuals aninhados**: confirmar qual fixture exercita `_emit_alias.expand`
  recursivo antes de confiar nos gates pra S2/S4/S5 (D1-D9 pode não cobrir).

## Recomendação ao owner

Fazer **Onda 1** (S0,S2,S3,S4,S5,S6 — EMIT-only + docs, byte-neutro, sem .pyx),
um step por commit com gate. **Onda 2 e S1 não recomendados** nesta rodada (DRY com
risco vs ganho de acoplamento baixo; .pyx sem rede de gate). Buraco do gate-pyx vira
item separado (ticket/nota), não bloqueia a Onda 1.
