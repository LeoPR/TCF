# 2026-08-17 — o que falta pro `.8`, e o veredito de CEP/telefone

**[probatório onde diz medido.]** Levantamento pedido pelo owner (workflow `wf_44910ef6-9f4`,
6 agentes, 5 lentes). 85 tickets no repo; ~27 abertos/in-progress/deferred.

---

## 1. O que falta pro `.8`

### (a) Já feito — só falta fechar o ticket (6 itens, esforço baixo)

Pendência de **papel**: o trabalho está no código, o checkbox não foi riscado. É o balde de
maior valor, e a sessão já tropeçou nele antes (a guarda de 128 níveis existia e ninguém
tinha documentado).

| ticket | prova de que já está feito |
|---|---|
| **T-CODE-TCF8H-JSON-PARITY** | `pytest tests/test_json_flow_parity.py -q` → **49 passed, 1 skipped, 0 xfail** (os 3 `xfail(strict)` viraram XPASS e foram promovidos). O ticket já declara `LACUNAS = {}` (:106) |
| **T-CODE-TCF8H-WELD** | W0–W5 todos `[x]` (:337-353); o único critério aberto (:436) é **contradito** por :425 no mesmo arquivo |
| **CLOSEOUT-2b** (API única) | `hasattr(tcf,'encode_hierarchical')` → **False**; `__init__.py:96-115` expõe só `encode` |
| **T-FMT-META-STRICT** (critério do KeyError cru, :80) | não reproduz mais — `decode('abc123')` → `ValueError` tipado (`syntax.py:851-856`) |
| **T-QA-8 / DOC-01** (README) | `grep 'TCF\.6\|Format 0\.7\|379 passed\|scripts/tcf_lazy' README.md` = **0 hits** |
| **CLOSEOUT-2e / F5** | default declarado NO-ACTION, nenhum blocker registrado |

*Borderline*: **T-DOC-3-shebang-terminology** tem os 2 critérios `✅ FEITO`, mas o owner
pediu para mantê-lo aberto como lembrete de errata. **Não mexer sem nova ordem.**

### (b) Cabe no `.8` e falta mesmo — o topo da fila

1. **`BUG-CHAVE-VAZIA-POSICIONAL`** — *o único caso em que o TCF **altera** o dado.*
   **Reproduzido por mim, agora:**
   ```
   encode({'': ['a','b']})              -> '#TCF.8M!'        decode -> {'0': [...]}  RT=False
   encode({'': ['a','b'], 'x': [...]})  -> '#TCF.8M!3,!x'    decode -> {'0': [...]}  RT=False
   ```
   Contraste que aponta a saída: **a mesma chave vazia no `.8H` fecha o round-trip** via `\z`
   — `encode({'': 'v'})` → `#TCF.8H#O\z`, **RT=True**. A rota `.8M` ganha a precedência
   quando o valor é lista, e é justamente a que não sabe representar a chave vazia.
   Bate o critério 1 de ROI do `T-REL-08:75` (fura a fila).
2. **F6/DOC-03** — a spec do formato ensina **duas coisas falsas**: diz "nature (cpf/cnpj/ip)"
   quando o registry tem **5** (`cnpj, cpf, data-iso, int-pad, ip`), e diz que id desconhecido
   dá "cru + warning" quando hoje é **`ValueError`** ("registry core fechado").
3. **F6/DOC-04** `pyproject.toml` sem `project.urls`/`classifiers` · **F6/DOC-05** scripts
   quebrados sem rótulo (`benchmark_compression.py:37` importa `encode_columns`, que não existe)
4. **CLOSEOUT-4a** — o comportamento de `view` **já é fail-loud** nos 3 casos de fronteira; só
   falta **pinar**
5. **F6-2** — `dist/` tem wheel `0.7.1` stale; falta a `py3-none-any` 0.8.0
6. **C3** — tag `v0.8.0` + Trusted Publishing, **sob GO explícito do owner**
7. **CLOSEOUT-3** — lab estrutural de natures com CNPJ real: declarado pré-`.9` obrigatório em
   3 lugares e **nunca rodou** (`find experiments/lab -iname '*cnpj*'` = vazio). **Decisão, não execução.**

### (c) Não cabe (só o id)

**`.9`** — `T-CODE-CORE-CONSOLIDATE` (C0 feito e verificado; C1/C2 são a abertura do
pós-release) · `T-CODE-PARALLEL-BUDGET` · `T-FLOW-ENCODE-STRATEGIES-TELEMETRY` ·
`T-FMT-ESCAPE-COMBINATORIAL-STUDY` · `T-FMT-QUOTING-STUDY` · `T-OPT-INFERENCE` ·
`T-TYPED-SINGLECOL-MODE-HEURISTIC` · os três `T-STUDY-*` · `T-MISTO-RLE-B64-SINGLE`
(derrubado 0/18 em real-world) · **nature CEP/telefone** (§2).
**1.0/2.0** — `T-FMT-OMIT-OR-DECLARE` · `T-SHAPER-NESTED-OUTPUT` · `T-CODE-OUTPUT-SINKS` ·
`META-TYPE-ENCODERS` (PARK v2.0).
**Ortogonal** — `META-STRATA-GOVERNANCE`: **G-1 vence 2026-08-18** (amanhã).

---

## 2. CEP e telefone — o veredito medido

**A pergunta era**: o `split`+`dict` que já existem resolvem, ou uma nature acrescenta?

**Resposta: os dois, e são coisas diferentes.** O `dict`/`split` resolvem a **repetição**; não
encolhem o **valor distinto**. A nature faz exatamente isso — **−24,1% em cima do que o core
já faz**, em coluna real de telefone.

Decomposição de `tpch.c_phone` (15 000 valores, **100% distintos**, RT=True em todos):

| | bytes | B/valor |
|---|--:|--:|
| texto cru | 239 999 | 16,00 |
| single-col `#TCF.8`, sem nature | 241 879 | 16,13 — **piora**; não tem split |
| `.8M` com **split**, sem nature | 158 104 | 10,54 — o split sozinho tira **−34,1%** |
| `.8M` split **+ nature** | **120 020** | **8,00** — a nature tira **−24,1% adicionais** |

**O mecanismo**: o `dict` deduplica repetições, mas a tabela de únicos **guarda o valor por
extenso**. O `split` quebra pela máscara. O que **nenhum mecanismo do core faz** é
**empacotamento de raiz** (12 dígitos → 7 chars base-80). Por isso soma, e cresce com a
cardinalidade.

### A condição que inverte a resposta: **cardinalidade**

| distintos | CEP mascarado | telefone BR |
|---|--:|--:|
| 0,2% | −1,0% | −1,5% |
| 2,0% | −4,8% | −6,7% |
| 15,0% | −21,2% | −29,3% |
| 39% | −29,3% | −42,2% |

**Abaixo de ~5% de distintos a nature não paga** (o `dict` já colheu). Isso **separa os dois
casos**: telefone é intrinsecamente ~100% distinto (**paga sempre**); **CEP depende da base** —
cadastro de bairro não paga, cadastro nacional paga.

### Três achados que mudam o enquadramento

1. **O registry de hoje não alcança.** `IntPadSpec` dá `format_noncanonical` em **200/200**
   CEPs (o guard rejeita zero à esquerda); em telefone cru o `zfill` é no-op → **+0,0%**.
2. **Não são duas natures — é UMA.** A mesma máquina genérica (`D dígitos → W chars base-80`,
   máscara fixa opcional) ganha em CEP mascarado (−35,2%), CEP cru (−23,3%), telefone
   mascarado (−51,9%), telefone cru (−31,6%) **e em 4 colunas reais que não são nenhum dos
   dois** (`municipio_id` −22,3%, `data_inicio` −13,7%, `municipio_cod` −8,1%,
   `cnae_principal` −5,9%). **O eixo é *código numérico de largura fixa*, não semântica brasileira.**
3. **Na tabela inteira dilui e não passa no gate.** `customer` (8 cols): **−2,16%**;
   `supplier` (7 cols): **−5,63%**. Nunca **piorou** (o FLOOR segurou) — contraste com o
   caveat CNPJ do F4 (+7339 B). Pelo gate declarado (≥15% weighted em 2+ reais): **passa na
   coluna, não passa na tabela.**

### Encaminhamento

O *"CEP → nenhuma ação"* de `STATUS.md:482` (pesquisa 2026-06-16) **não se sustenta mais como
afirmação geral**: aquela pesquisa mediu OBAT/prefixo e concluiu que "o TCF já trata" — não
mediu **empacotamento de raiz**, que vale 24,1% em cima do split. Mas o destino **continua o
`.9`** (`ROADMAP.md:87`, FILTROS-POPULARES). O que muda é o **motivo**: não é "não paga", é
**"paga na coluna, não na tabela, e o `.8` não abre spec novo"**.

---

## 3. Não alcançado (declarado)

- **Não existe coluna de CEP em dado real.** Varredura no header de todo `.csv` de
  `Z:/tcf-data`: 6 hits, **todos** `c_phone`/`s_phone` do TPC-H. **Todo número de CEP aqui é
  sintético.** Confirma `ROADMAP.md:87` ("o gargalo é DADO").
- O telefone "real" é **TPC-H** (`NN-NNN-NNN-NNNN`, dbgen), **não** telefone BR. Mesma classe,
  prova diferente.
- Suíte completa não rodada (só `test_json_flow_parity`). **Sem pin novo de contagem.**
- **Só bytes** — nada de CPU/latência da nature candidata.
- A spec medida é **candidata, não soldada**: máscara é template fixo por variante. Um spec de
  verdade precisa de DSL/IR (ligado ao `CLOSEOUT-3`).
- Uma lente chegou **truncada**; `T-8H-UM-CANDIDATO-SO` e `T-META-NAO-DECLARA-MODO` aparecem
  só como linha no STATUS, **sem arquivo de ticket** — não entraram na fila.

## Conexões

- Labs do dia: [`0400`](../../2026-08/2026-08-17/2026-08-17-0400-o-candidato-unico-do-H/) ·
  [`0500`](../../2026-08/2026-08-17/2026-08-17-0500-header-do-H-sintetico/) ·
  [`0600`](../../2026-08/2026-08-17/2026-08-17-0600-limites-de-profundidade-do-H/) ·
  [`0800`](../../2026-08/2026-08-17/2026-08-17-0800-prevalencia-nos-sinteticos-de-controle/)
- `tickets/T-REL-08-CLOSEOUT.md` · `tickets/BUG-CHAVE-VAZIA-POSICIONAL.md` · `ROADMAP.md:87`
