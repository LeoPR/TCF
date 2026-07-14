# Convenções do dirty-lab — checklist obrigatório [dispositivo]

**Data**: 2026-07-05 (consolidado após incidente: um lab reportou números só em prosa, com `trace/` e
`output/` vazios — "só sua palavra, sem valor científico"). Consolida as normas espalhadas em
`CLAUDE.md §CONVENÇÕES`, e nas memórias de feedback: [[feedback-outputs-visiveis-para-auditoria]],
[[feedback-dirty-lab-outputs-e-progressao-dados]], [[feedback-dirty-lab-filosofia]], [[feedback-sempre-cross-reference]].
**Antes de fechar qualquer sub-exp, rodar este checklist.**

## 1. Nomeação, ordenação e ESTRUTURA (refinado 2026-07-13 — pedido recorrente do owner, 10+ vezes)

- Lab: `experiments/lab/dirty/YYYY-MM-DD-HHMM-descricao/` — **só o dia NÃO basta** (labs do mesmo dia
  ficam sem ordem); pôr **hora-minuto** (ou versão `-vNN-`) + descrição do que está sendo feito.
- **Pastas por ESTÁGIO, com numeração DENTRO de cada uma** (supersede o "nunca pastas por estágio"
  antigo — o problema era estágio SEM número; com número dentro, resolve):

  ```
  lab/
  ├── README.md · result.md · run.py · datasets-provenance.md
  ├── inputs/          entradas COM EXTENSÃO REAL: .json, .csv, .tcf, .jsonl…
  ├── intermediates/   fluxo interno: semântica, traces, canônicos p/ diff (.txt p/ prosa; .json etc. pelo conteúdo)
  └── outputs/         saídas COM EXTENSÃO REAL (.tcf, .json, .csv) + roundtrip + contraprova + bytes
  ```

- **EXTENSÃO = o formato do conteúdo, SEMPRE**: JSON→`.json`, tabular→`.csv`, wire TCF→**`.tcf`**
  (labs têm exceção no `.gitignore`: `!experiments/lab/dirty/**/{inputs,outputs}/**/*.tcf` — evidência de lab é versionada
  com a extensão real; o `.tcf.txt` antigo era workaround, não usar em lab novo). `.txt` só para
  prosa/debug/contraprova.
- **Roundtrip é ARQUIVO diffável na extensão da entrada**: `outputs/NN-nome.roundtrip.json` deve ser
  **byte-idêntico** ao canônico em `intermediates/` (assert no `run.py` + o leitor pode dar `diff`).
- Sub-experimentos (quando houver): `NN-descricao/` numerados dentro do lab.
- Gabarito desta estrutura: `experiments/lab/dirty/2026-07-13-2019-especiais-formatos-lado-a-lado/`.

## 2. O laboratório contém a EVIDÊNCIA, não a minha palavra (regra-mãe)

**Anti-padrão proibido**: computar em memória / scratchpad, reportar tabela em prosa, deletar outputs.
Todo número citado tem de vir de um **arquivo no lab**. `python run.py` regenera tudo.

Todo sub-exp DEVE conter, no disco visível (não gitignored):
- **`run.py`** (+ libs) no lab — reproduzível: `python .../run.py` gera todos os artefatos.
- **Output TCF real**: `outputs/NN-*.tcf` (desde 2026-07-13 o `.gitignore` tem exceção para labs;
  o `.tcf.txt` de labs antigos fica como histórico). Byte-a-byte, inspecionável.
- **Trace interno OBAT/HCC**: `artifacts/NN-obat-hcc-trace.txt` (via `SideOutputs` — `obat_log`, `hcc_trace`,
  `cadence_info`, `seq_rle_runs`, `body_bytes`, por coluna). É como se vê "como construíram".
- **Round-trip provado em arquivo**: `artifacts/NN-roundtrip.txt` — `decode(encode(x))==x` (nível dado
  E, se houver reconstrução de estrutura, nível objeto), com **OK/MISMATCH por item**. Mismatches: lista
  COMPLETA, não truncada; destaque visual (RT FAIL em seção própria).
- **Entradas** (`inputs/` ou `01-input`) + **proveniência** (`datasets-provenance.md`): origem +
  anonimização + viés declarado.
- **Amostra de intermediários** quando houver pré-tx (ex.: primeiras 20 strings pós-normalização).

Regra byte: **NUNCA reportar bytes sem RT validado**. E sempre **listar os paths** dos artefatos gerados na resposta.

## 3. README com estado + progressão

- README do lab: **estado era/foi/é/será**, fluxo (com rastreabilidade), lista de arquivos, "como rodar",
  ticket linkado.
- **Progressão de dados** (o lab inteiro cobre; cada sub-exp pode focar 1 etapa):
  ilustrativo/forçado → realista (>1k, ruído) → bordas (N=0/1, 100% igual/distinto) → extrapolação (10-100×).
- Vocabulário disciplinado: nada de "melhor" sem "em qual cenário, segundo qual métrica". Sem superlativos.

## 4. Vínculo (achabilidade > cautela)

- Todo lab/resultado linka a um **ticket** (`tickets/T-*`) e à nota/registro de hipótese
  (`roadmap-hipoteses.md`); cross-link bidirecional; entrada nos índices (MAP/STATUS quando for ponto de entrada).

## 5. Filosofia (não esquecer)

- Dirty é **engenhoca descartável**: prova a IDEIA, depois **abre zero** no proto formal (não copia código dirty).
- `src/tcf` **intocado** sem aprovação; labs são FORK.
- Reorg em massa: TodoWrite + (commit antes se já versionado) + validação após.

## Gabarito (lab de referência)

`experiments/lab/dirty/2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/` (e `2026-06-27-gdict-b2-prototype/`):
`run.py` + `artifacts/NN-*` (entrada → tradução → `.tcf.txt` adaptado → decode → bytes) + `result.md` +
`README.md` + `datasets-provenance.md`. **Nome com dia+HHMM+descrição** (ordenável, não só o dia).
