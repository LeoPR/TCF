# Mapa de sincronização — documentação × código (auditoria 2026-08-16)

> **Owner (2026-08-16)**: *"nós testamos muito com o H, depois de pronto fizemos as views/lazy,
> depois começamos as revisões para fechar os tipos e assim por diante. Provavelmente essas
> revisões quebraram e pode ter deixado coisa pra trás. Logo precisamos ter certeza que tanto
> código como ideias estão atualizados, mesmo que atualmente quebrados pelas últimas mexidas.
> Pode gastar um tempo estudando isso primeiro antes de fazer qualquer código."*

## Como foi feito, e o que NÃO foi coberto

Varredura em 6 superfícies paralelas — **233 documentos lidos** (41 ADRs + índice, 28 docs
públicos com os exemplos RODADOS, 21 notas do H/lazy, 29 notas+tickets de tipos, STATUS.md
inteiro + 84 tickets, e uma auditoria INVERSA de 34 módulos de `src/tcf/` procurando código
que doc nenhum descreve). **97 defasagens reivindicadas.**

> ⚠️ **Limitação minha, declarada**: eu capei o verificador adversarial em **28 das 97**
> reivindicações, e **não registrei o corte** — violando a regra do próprio projeto de nunca
> truncar cobertura em silêncio. Das 28 verificadas, **23 procederam e 5 caíram**. As **69
> restantes seguem NÃO-VERIFICADAS** e não devem ser tratadas como achado até passarem pelo
> mesmo gate. O material bruto está no journal do workflow `wf_4e9c88cb-b10`.

Nada foi modificado — nem `src/`, nem `docs/`, nem os `.md` da raiz. Os agentes tinham
proibição explícita. **Nenhum conserto foi feito**, conforme o pedido.

---

# MAPA DE SINCRONIZAÇÃO — documentação × código (auditoria 2026-08-16)

> Estado da árvore: `main` limpo, suíte **1285 passed / 3 skipped** (reportado por 2 superfícies independentes; bate com `STATUS.md:78`). Nada foi modificado. Todo item abaixo foi re-conferido por execução ou leitura direta nesta síntese.

---

## 1. Veredito (3 linhas)

**Confirma-se, em grau parcial e datável.** 14 defasagens verificadas, distribuídas em três camadas — 9 documentos vivos (`README*`, `docs/vocabulary.md`, `docs/reference/`, `docs/algorithms/`), 11 ADRs + o índice `docs/adr/README.md`, e 3 módulos de `src/tcf/` (prosa interna) — todas rastreáveis a 6 mexidas: flip de defaults (14/06), corte do legado `.6`/`.7` (ADR-0032, 09/07), revogação do forward-compat de nature (BUG-13b, 10/07), weld hierárquico (ADR-0033, 14/07), `[]` flat (24/07) e delimitador de polaridade (ADR-0035, 26/07).

**O grau é "documentação atrás do código", não "código quebrado".** Nenhuma das 14 corresponde a bug de codec; a suíte está verde e os pins dos testes estão certos. Das reivindicações que chegaram ao verificador adversarial, 5 caíram — 3 delas por confundir **registro datado** (ADR aceito, nota de lab) com **spec viva**, o que é o critério mais reutilizável que esta auditoria produziu.

**A formulação exata do owner ("deixaram coisa pra trás") é mais precisa que "quebraram".** O que ficou para trás foi (a) o único artefato de vigência que a convenção permite editar — `docs/adr/README.md` — e (b) a prosa dentro de `src/tcf/`, que não tem gate nenhum. `docs/reference/encode-knobs.md` e `api.md` acompanharam os dois flips de default de 14/06 e falharam nos dois pontos do `.8H`/`[]`.

---

## 2. Achados por severidade

Critério de tier: **engana-quem-lê** = alguém implementando a partir do doc produz erro demonstrável (perda de dado, wire inválido, exemplo que não roda). **Incompleto** = o doc não mente sobre o que descreve, mas não cobre o que o código passou a fazer, ou o campo de vigência não foi atualizado. **Cosmético** = residual sem consequência de porte.

---

### 2.1 ENGANA QUEM LÊ (9)

---

**E1 — `docs/algorithms/output-convention.md` manda o decoder skipar linhas `[` e `]`; o skip foi removido em 2026-07-17 e hoje elas são células válidas**

- **Doc diz:** "Decoder deve continuar aceitando brackets isolados como linhas ignoradas (backwards compat com M7 e anteriores)", com bloco de código `if not linha or linha in ("[", "]"): continue  # mantem skip de brackets para back-compat`.
- **Código faz:** o skip foi removido sob `BUG-BRACKET-CELL-LOSS` (fix 2026-07-17, aprovação do owner) — engolia célula calado. RT exato hoje.
- **Doc:** `docs/algorithms/output-convention.md:71-83` (espelho histórico, imutável: `docs/adr/0006-empty-string-decode-fix.md:39-40,49-50`)
- **Código:** `src/tcf/composicional/syntax.py:918-923`. Rodado: `tcf.decode(tcf.encode(['a',']','b','[']))` → `['a', ']', 'b', '[']`.
- **Correção:** substituir a seção `## Decoder` (`:73-83`) por: *"O decoder NÃO skipa `[`/`]`. O skip era back-compat de formato bracketed (M7 e anteriores) e engolia célula calado — removido em 2026-07-17 (`BUG-BRACKET-CELL-LOSS`). Linha vazia decoda como string vazia (ADR-0006, decisão principal, ainda vigente)."* Manter o loop de exemplo apenas com `if not linha` removido também — o ADR-0006 já tinha tirado esse.
- **Por que é o topo do tier:** é o único cujo erro de porte é **perda silenciosa de dado**, e o doc é referência viva citada por `docs/algorithms/README.md:20` e `docs/algorithms/core-data-model.md:133` — não tem a cobertura de imutabilidade que o ADR-0006 tem.

---

**E2 — `docs/vocabulary.md` descreve o marcador `!` (raw) com o corpo do modo oposto e com a condição de vitória invertida**

- **Doc diz:** `` `!<size>=<name>` — modo **raw** (V2-A): body em TCF puro (OBAT+HCC); fallback quando TCF < raw ``
- **Código faz:** `!` é raw literal — corpo = `"\n".join(valores)`, sem OBAT/HCC, decode = `split("\n")`; vence quando `len(raw) < len(tcf)`. Duas inversões na mesma linha. A linha `:49` (modo sem prefixo) já descreve corretamente OBAT+HCC — ou seja, o doc dá o mesmo corpo a dois modos opostos.
- **Doc:** `docs/vocabulary.md:46` (confirmado por leitura direta)
- **Código:** `src/tcf/multi/core.py:22`, `:461-463` (encode) e `:648`,`:731` (decode)
- **Correção (linha literal):** `` - `!<size>=<name>` — modo **raw** (V2-A): body = `"\n".join(valores)`, texto literal SEM OBAT/HCC (decode = `split("\n")`); vence quando `len(raw) < len(tcf)` e nenhum valor tem `\n` embutido (`_fallback_safe`) ``
- **Nota de origem:** o verificador estabeleceu que a linha **nasceu errada** em `44010460` e escapou da passada M4 (`44d66cfe`). Não é regressão do weld de tipos — é erro de origem num doc que `AGENTS.md` aponta como vocabulário controlado. Ancoras corretas para copiar: `docs/adr/0022:61`, `docs/reference/encode-knobs.md:34-35`, `docs/algorithms/TCF-format.pt-BR.md:107,301-302`.

---

**E3 — `docs/algorithms/TCF-format.*` fecha o discriminador em 5 valores e declara `H` "reservado, fail-loud"; `H` roteia para o codec real desde 2026-07-14 e o índice 6 aceita 9 valores + 26 pontuações**

- **Doc diz:** "o caractere logo apos `#TCF.8` decide a estrutura. **5 valores**", tabela com `\n`/*(nada)*/`M`/`H`/` `, linha do `H` marcada `` **reservado** (ADR-0031; codec no lab, fail-loud) ``, e o remate "Discriminador desconhecido/reservado (**incl. `H`**) -> **fail-loud** no decode".
- **Código faz:** `H` roteia para `tcf.hierarchical.decode_hierarchical`; o índice 6 aceita `M`, `H`, ` `, `` (stamp), `b`/`n`/`s` (tags de tipo), `B`/`C` (bN de domínio) = 9, mais uma faixa de 26 caracteres de pontuação (`!"#$%&'()+-./:;<=>?@[]_\`{}`) consumida pelo pré-passe de polaridade (ADR-0035).
- **Doc:** `docs/algorithms/TCF-format.pt-BR.md:64-78` e espelho `docs/algorithms/TCF-format.en.md:60-72` (confirmado por leitura)
- **Código:** `src/tcf/decoder.py:163` (polaridade), `:176-179` (H), `:184`+`:312` (`_TAGS_TIPO = {b,n,s}`), `:190`+`:310` (`_DISCS_BN = {B,C}`), `:198` (fail-loud residual). Rodado: `tcf.decode('#TCF.8H#E\n')` → `{}`.
- **Correção:** trocar "5 valores" por "9 valores + sufixo de polaridade"; adicionar linhas `b`/`n`/`s` (single-col tipado, ADR-0038 + weld T-BN-TIPADO) e `B`/`C` (bN de domínio, ADR-0036); reescrever a linha do `H` para `` multi-col hierarquico — **welded** (ADR-0033, 2026-07-14) ``; e o remate para "Discriminador fora do conjunto acima -> fail-loud (52 chars ASCII printáveis caem aqui; os dígitos caem antes, no fail-loud de VERSÃO, `decoder.py:143-149`)".
- **Defeito adjacente na mesma tabela (cosmético, ver C3):** a linha do version-stamp aparece duas vezes (`:70-71` e `:76`).

---

**E4 — ADR-0027 e `docs/algorithms/TCF-format.*` prometem "id de nature desconhecido → valor cru + warning" (forward-compat); o código levanta `ValueError` nas 3 rotas de decode e na view**

- **Doc diz:** ADR-0027: `` "ID desconhecido -> fallback explicito: retorna valor CRU (sem reverter pre-tx) + SideOutputs.unknown_nature_ids (NAO KeyError, NAO silencioso) -> forward-compat" ``; e a nota WELDED do topo afirma como fato consumado "Commit do MVP + 9 testes (... unknown-id cru+warn ...)". `TCF-format`: "`:id` da nature ... id desconhecido -> cru + warning, precedencia header-vence" (confirmado por leitura).
- **Código faz:** `_resolve_header_spec` levanta `ValueError('nature-id desconhecido no header ...')` nas três rotas (single, single-tipado, multi); a view levanta na materialização. A revogação está registrada **no teste**, não em ADR: `"Id desconhecido -> ERRO (T-QA-8 BUG-13b, owner 2026-07-10): revoga o forward-compat de 2026-06-24"`. O campo `SideOutputs.unknown_nature_ids` nunca existiu.
- **Doc:** `docs/adr/0027-nature-mark-header-self-describing.md:11-12,17-18,74,131-132`; `docs/algorithms/TCF-format.pt-BR.md:86-87`; `docs/algorithms/TCF-format.en.md:80-81`
- **Código:** `src/tcf/decoder.py:84-88`, `src/tcf/view.py:156-159`, `tests/test_natures.py:263-270` (`test_unknown_nature_id_raises`), `tests/test_f0_boundary_fixes.py:689,693,700`. Rodado: `tcf.decode('#TCF.8 col:zzz\nabc\n')` → `ValueError: nature-id desconhecido no header single-col: 'zzz' — registry core fechado...`
- **Correção — separada por camada:**
  - `TCF-format.pt-BR.md:86-87` / `.en.md:80-81` (**vivos, edição in-loco**): trocar "id desconhecido -> cru + warning" por "id desconhecido -> **fail-loud** (`ValueError`); registry core é fechado. Rota de escape para id externo: `dataclasses.replace(SPEC, wire_id=<id do header>)`".
  - ADR-0027 (**imutável**): ADR novo que supersede o item *forward-compat por id desconhecido*, registrando BUG-13b / T-QA-8 (owner 2026-07-10), com back-link a partir de `0027` na forma já usada em `0027:23-28` (nota de refino do 0029), e Status atualizado em `docs/adr/README.md:57`.
- **Ressalva de escopo (correção do verificador ao auditor):** das 5 menções no ADR-0027, apenas `:11-12`, `:17-18`, `:74` e `:131-132` são afirmações não-hedgeadas. `:82`, `:86` e `:99` estão sob seções `"## Scope / diff (se implementar)"` e `"## Testes (se implementar)"` — só viram defasagem porque a nota WELDED de `:9-10` declara "Implementado ... exatamente como desenhado abaixo". Não citar `:99` como leg principal.

---

**E5 — `docs/reference/api.md` e `docs/reference/json-equivalence.md` afirmam que `encode([])` produz `.8H` `#D0` (11 B); o encode público emite `#TCF.8` (7 B) desde 2026-07-24**

- **Doc diz:** `api.md`: "`encode([])`/`encode({})` deixaram de ser fail-loud e viram `.8H` (`#D0`/`#E`, representáveis)". `json-equivalence.md`: linha de tabela `| **raiz = `[]` / `[{}]` / `[{},{}]`** | P4b | `#TCF.8H#D0` · `#D1` · `#D2` | ✅ |`. ADR-0033 `:367` na tabela de custos: `` `[]` 11 B ``, e a emenda de 2026-07-23 (`:3-9`) declara "Nenhum byte de wire foi tocado".
- **Código faz:** `encode` intercepta a lista vazia **antes** da rota `.8H` — "`[]` FLAT (owner 2026-07-24, canonicidade do vazio)". `#D0` continua decodável, mas deixou de ser a grafia canônica.
- **Doc:** `docs/reference/api.md:57`; `docs/reference/json-equivalence.md:71`; `docs/adr/0033-hierarchical-codec-weld.md:3-9,367-368`
- **Código:** `src/tcf/encoder.py:504-518` (commit `1fbc9f5c`, que tocou 0 arquivos em `docs/`). Rodado: `tcf.encode([])` → `'#TCF.8\n'` (7 B); `_encode_hierarchical([])` → `'#TCF.8H#D0\n'` (11 B); `decode` aceita as duas → `[]`.
- **Correção:** `api.md:57` → "`encode([])` emite `#TCF.8\n` (7 B, rota flat — canonicidade do vazio, 2026-07-24); `encode({})` vira `.8H` (`#E`). `#TCF.8H#D0` continua **decodável** mas não é mais a grafia canônica de `[]`." `json-equivalence.md:71` → separar a raiz `[]` (canônica `#TCF.8`) das raízes `[{}]`/`[{},{}]` (`#D1`/`#D2`).
- **Não citar `0033:354`** ("`#D<N>` ([] · [{}]xN)") como defasado — é enunciado de **gramática** e continua verdadeiro; uma mudança de dispatch não o falsifica. O erro real de porte não são os 4 B: é canonicidade — um segundo porte seguindo o ADR emite 11 B, decoda certo, passa RT por valor, e só falha num gate byte-exato (`encode(decode(w)) != w`).

---

**E6 — O exemplo-vitrine do `view()` no `README` não roda: importa de `tcf_lazy`, que não existe no pacote instalado**

- **Doc diz:** `from tcf import encode` / `from tcf_lazy import view   # scripts/ on sys.path`, seguido de 6 consultas e da legenda *(Real PoC output)*.
- **Código faz:** `ModuleNotFoundError: No module named 'tcf_lazy'` — confirmado nesta síntese. O shim mora em `scripts/tcf_lazy/`, e `pyproject.toml` empacota só `src/tcf`, então quem faz `pip install tcf-format` nunca tem `tcf_lazy`. O caminho canônico é `from tcf import view` (`'view' in tcf.__all__` → `True`, `len(__all__) == 15`).
- **Doc:** `README.md:449` e espelho `README.pt-BR.md:454`
- **Código:** `src/tcf/__init__.py:106`, `pyproject.toml:67-68`; contraste com `docs/reference/api.md:9`, `MAP.md:122`, `src/tcf/view.py:7` — os três já mandam usar `from tcf import view`.
- **Correção:** trocar a linha de import por `from tcf import encode, view`. O resto do bloco não muda: com o import corrigido, ele roda inteiro e todos os valores da legenda batem (183 B, count 6, sum 750.0, avg 125.0, max/min 200/80, `where.count` 4, `where.sum` 470.0). Custo de 1 linha, em 2 arquivos.

---

**E7 — ADR-0023 declara `min_header` default `False` e promete que o default preserva o header v1 `#TCF.6`; o default é `True` desde 2026-06-14 e nenhum valor do knob produz v1**

- **Doc diz:** "**Default `min_header=False`** -> header v1 (`# <s>=<n>,...`), `#TCF.6`, byte-identico (invariantes D1-D9=1523B, D17a=322B preservados). Segue o padrão do codebase (opt-in; default preserva byte-canonical)."
- **Código faz:** `min_header: bool = True`; o header v1 com prefixo `# ` e sizes decimais foi cortado por ADR-0032 §4. `min_header=False` hoje entrega `#TCF.8M!e=a,!5=b` — `.8` com size explícito, não v1.
- **Doc:** `docs/adr/0023-v2-minimal-header-weld.md:32` + `docs/adr/README.md:53` (que ainda diz "opt-in `min_header`", confirmado por leitura)
- **Código:** `src/tcf/encoder.py:234`, `src/tcf/multi/core.py:277,297-301`
- **Correção:** o **corpo** do ADR é imutável e datado — não editar. O que falta é: (a) Status em `docs/adr/0023:3` com stamp de supersessão parcial; (b) `docs/adr/README.md:53` → "**accepted** (default flipado para `True` em 2026-06-14; header v1/`#TCF.6` cortado por 0032 §4)". O flip do default foi feito por commit (`d8b537a5`) sob a regra do próprio `docs/adr/README.md:78` ("Crie ADR quando ... vai mudar comportamento público").
- **Assimetria com ADR-0022 (deliberada):** `0022` instrui `fallback=True` — seguir é no-op e entrega o comportamento certo, por isso ele fica no tier I. `0023` instrui `min_header=False` prometendo v1 — seguir **erra**, por isso fica aqui. Doc viva já está certa nos dois casos (`encode-knobs.md:10,28-29,41-43`; `api.md:65`).

---

**E8 — `src/tcf/decoder.py`: o docstring do módulo e dois comentários de constantes ficaram atrás de três mexidas (corte do legado, weld H, alargamento de `_TAGS_TIPO`)**

Três defeitos no mesmo arquivo, todos confirmados por leitura direta nesta síntese:

| # | Doc (linha) | Diz | Código faz |
|---|---|---|---|
| a | `src/tcf/decoder.py:5-8` | "`#TCF.7 M\n` (**vivo**) ou `#TCF.6 M\n` (LEGADO, leitura até o 1.0) -> multi-column ... caso contrário -> single-column, retorna `list[str]`" | `:138-142` levanta `ValueError` para `.6`/`.7`; `:143-149` levanta para qualquer `#TCF.<N≠8>`; `:198-199` levanta para disc desconhecido; `#TCF.8H` devolve `dict` via `:176-179`. São 10 rotas terminais, não 2. |
| b | `src/tcf/decoder.py:59-60` | "`'H'`=hierarquico **RESERVADO** (ADR-0031, codec no lab -> fail-loud)" | `:176-179` roteia para `tcf.hierarchical.decode_hierarchical`. Rodado: `decode('#TCF.8H#E\n')` → `{}`. |
| c | `src/tcf/decoder.py:279-282` | "Whitelist do DECODE = só o que o encoder EMITE. Hoje: bool. `'n'`/`'s'` ficam RESERVADOS ... mas **NÃO decodáveis ainda** -> caem no fail-loud" | `_TAGS_TIPO = frozenset({"b","n","s"})` roteia os três; `_cast_tipo` tem ramo `n` completo (`:333-382`) e `s` identidade (`:383`). Rodado: `decode('#TCF.8s\nabc\n')` → `['abc']`; `encode([1,2,3])` → `'#TCF.8n\n*3+1|\1\n'`. |

- **Correção (a):** reescrever `:5-8` para listar o dispatch real (`.6`/`.7` → `ValueError` (ADR-0032); versão ≠ 8 → `ValueError`; `H` → hierárquico, `dict`; `b`/`n`/`s` → single-col tipado; `B`/`C` → bN de domínio; `M` → multi; ` `/`` → single; órfão → single). Nota: o docstring da **função** logo abaixo (`:101-106`) já está correto — a contradição é interna ao arquivo. E `:30-31` ("outputs sem shebang tratados como single-col") **continua verdadeiro** (`decode('abc\nabcd\n')` → `['abc','abcd']`) — não usar como reforço sem ressalva.
- **Correção (b):** `'H'`=hierárquico **welded** (ADR-0033, 2026-07-14) -> `decode_hierarchical`.
- **Correção (c):** whitelist = `{b, n, s}`; encoder emite `b` (slots, ADR-0038) e `n` (desde **2026-07-25**, `fe939eef` — não 2026-08-07, que foi o weld T-BN-TIPADO da canonicidade por re-emissão); `s` é **decodável-não-emitido**, mesmo contrato do modo `C` do ADR-0036. A frase "simetria estrita: só o que o encoder emite" não descreve mais a whitelist e precisa ser reformulada, ou o `s` sai dela.
- **Padrão embutido:** o commit `fe939eef` alargou `_TAGS_TIPO` e deixou o comentário intocado **no mesmo hunk**.

---

**E9 — `src/tcf/__init__.py` anuncia D1-D9 = 1586 B e cita como fonte os dois testes que pinam 1545**

- **Doc diz:** `- D1-D9 sint: 1586B em 2981 raw = 53.2% ratio (RT 9/9; inclui header default ADR-0034) [1586B pinado em test_core_rt.py + test_regression_v1_baseline.py]` — é o docstring do pacote, o que `help(tcf)` mostra primeiro, e o mesmo bloco declara "Números abaixo são probatórios: o TESTE mede, a prosa aponta".
- **Código faz:** os dois testes citados pinam **1545**. Confirmado nesta síntese: `tests/test_regression_v1_baseline.py:96` → `D1_D9_TOTAL = 1545  # sum acima. 1523 -> 1586 (+63 = 9 x 7 B de header, ADR-0034)`. O 1586 foi a era do header-default (ADR-0034, 24/07); o delimitador de polaridade (ADR-0035, 26/07) levou a 1545 (−41 em D5/D6). O ratio derivado também está defasado.
- **Doc:** `src/tcf/__init__.py:56-57`
- **Código:** `tests/test_core_rt.py:216`, `tests/test_regression_v1_baseline.py:96`
- **Correção (linha literal):** `- D1-D9 sint: 1545B em 2981 raw = 51.8% ratio (RT 9/9; inclui header default ADR-0034 + delimitador de polaridade ADR-0035) [1545B pinado em test_core_rt.py + test_regression_v1_baseline.py]`. Três valores mudam (1586→1545, 53.2%→51.8%, +ADR-0035); "2981 raw" foi medido e confere.

---

### 2.2 INCOMPLETO (6)

---

**I1 — `docs/adr/README.md` deixou de ser mapa de vigência: 6 linhas de Status carimbam estado revogado**

Este é o item de maior alavancagem do tier — é o **único** artefato que a convenção de imutabilidade (`docs/adr/README.md:8-11`) permite editar, e é o que ninguém editou. Linhas confirmadas por leitura:

| linha | Status atual | Estado real |
|---|---|---|
| `:35` | 0005 anuncia "hooks" como terço da decisão | hook nunca existiu versionado (ver I6) |
| `:36` | 0006 sem nota | superseded-parcial em 2026-07-17 (ver E1) |
| `:52` | 0022 "opt-in `fallback=True`" | default `True` desde 2026-06-14 |
| `:53` | 0023 "opt-in `min_header`" | default `True` desde 2026-06-14 (ver E7) |
| `:55-56` | 0025/0026 sem nota | magic `#TCF.7` cortado por 0032 §4 (ver C1) |
| `:57` | 0027 "accepted (MVP welded 2026-06-24)" | forward-compat revogado em 2026-07-10 (ver E4) |
| `:61` | 0031 "char reservado, **codec nao-weldado**"; descrição "codec hierárquico (EXP-015) **segue** research-track, weld gated" | weldado em 2026-07-14 (ADR-0033, `a20ddf71`) |

- **Precedente que prova que o campo é mantido:** `:43`, `:47` e `:54` já carregam notas desse tipo (`0024` → "refinado por 0028"; `0017` → parte superseded; `0013`). Logo isto é *stale*, não imutabilidade.
- **Correção:** uma passada única na coluna Status, na forma já usada em `:54`.

---

**I2 — ADR-0029/0031 fixam a tabela de discriminadores em 4/5 valores e declaram "discriminador do `.8` fechado e sem colisão"; e ADR-0034 manda o leitor de 24/07 em diante para essa tabela**

- **Doc diz:** `0029:77-83` tabela `M`/`H`/espaço/`\n`; `0031:27-36` "passa a ter **cinco** valores", `:87` "Discriminador do `.8` fechado e sem colisão"; `0034:5-6` declara explicitamente que "a tabela de discriminadores" do 0029 "continua válido".
- **Código faz:** 9 valores + faixa de 26 pontuações (medição do verificador; a versão do auditor dizia 24). Os 5 novos entraram por ADR-0036 (`B`/`C`) e pela rota tipada (`b`/`n`/`s`), que **não tem ADR próprio**.
- **Doc:** `docs/adr/0029-...:77-83`; `docs/adr/0031-...:27-36,87`; `docs/adr/0034-...:5-6`
- **Código:** `src/tcf/decoder.py:163,176,184,190,198,310,312`
- **Correção:** os corpos de 0029/0031 são datados e não se editam. O que falta é (a) o ADR ausente da **rota tipada** `b`/`n`/`s`, que é a única extensão do discriminador sem registro de decisão, e (b) `0034:5-6` — que é afirmação no **presente** sobre estado corrente ("continua válido") e por isso é o alvo legítimo; a tabela viva corrigida vive em `docs/algorithms/TCF-format.*` (ver E3).
- **Precisão de evidência (correção do verificador):** 26 chars de pontuação roteiam; 52 chars caem no fail-loud de discriminador; os dígitos 0-9 caem antes, no fail-loud de **versão** (`decoder.py:143-149`) — não são exemplo de discriminador desconhecido.

---

**I3 — `docs/adr/0031:3` e `docs/adr/0032:5` não ganharam stamp de supersessão apontando para 0033**

- **Doc diz:** `0032:32-35` (§2), no presente: "o `.8` **reconhece** `#TCF.8H` como modo **conhecido-mas-não-implementado** (fail-loud, §6) — o **codec** hierárquico vai pro **lab**". Falso desde 14/07.
- **Código faz:** `src/tcf/decoder.py:176-179` roteia; `src/tcf/hierarchical.py` tem 999 linhas.
- **Correção:** stamp no campo `Status` de ambos, na forma de `0029:3-6` ("**DEFAULT SUPERSEDIDO** pelo ADR-0034"). A prática do repo é inconsistente (`0027:3` foi superseded por 0032 e não recebeu stamp), então isto é recomendável, não defeito duro.
- **NÃO procede (over-claim removido pelo verificador — registrar para ninguém re-abrir):** `0031:55-60` ("`src/tcf` **não muda** com este ADR") e `0032:77` (§Escopo NEGATIVO, "Codec hierárquico **não weldado**") continuam **verdadeiros** — são enunciados sobre o escopo daquele ADR. `0031:61-62`, `0031:94-95` e `0032:57-58` são autolimitados ("Até weldar", "até o weld gated") e estão corretos como corpo datado. O back-link exigido pela convenção **existe** (0033 aponta para 0031).

---

**I4 — ADR-0006 é superseded-PARCIAL e não tem banner**

- A decisão-titular (linha de body vazia decoda como string vazia) **continua vigente** — medido: `['a','','b']` → `['a','','b']`. Defasada é só a cláusula acessória "manter `linha in ("[","]")` pra back-compat" (`docs/adr/0006:39-40,49-50`), revertida em 2026-07-17 (`src/tcf/composicional/syntax.py:918-923`).
- O fecho **está** registrado — em `docs/adr/0033:370` (§Update P4b: "o par R0 ... foi fechado no L1") e em `STATUS.md:265` — mas nunca voltou ao 0006 nem ao índice.
- **Correção:** o mesmo formato de supersede-parcial já usado em `docs/adr/0017:15` + `docs/adr/README.md:47`, aplicado a `0006` + `docs/adr/README.md:36`. **Se só um dos dois lugares for corrigido, corrija E1** (`output-convention.md`), não este.

---

**I5 — `docs/reference/encode-knobs.md` abre com o enquadramento do regime opt-in, contradito pela própria tabela 25 linhas abaixo**

- **Doc diz:** `:3-5` — "Referência dos parâmetros **opt-in** de `tcf.encode`. O uso sem argumentos produz o formato 0.8 / `#TCF.8M` sem perdas; os parâmetros abaixo **só mudam bytes/layout quando passados explicitamente**."
- **Código/doc faz:** a assinatura no bloco imediatamente seguinte (`:8-9`) já mostra `fallback=True, min_header=True`, e a tabela `:28-29` os lista com default `True` e efeito de byte não-nulo ("economiza bytes de header"). Confirmado por leitura.
- **Doc:** `docs/reference/encode-knobs.md:3-5` vs `:8-9`, `:28-29`
- **Correção:** trocar `:3-5` por "Referência dos parâmetros de `tcf.encode`. Dois (`fallback`, `min_header`) são default `True` e já agem no uso sem argumentos; os demais só mudam bytes/layout quando passados explicitamente." É o resíduo textual do mesmo flip de 14/06 que produziu E7 e o item ADR-0022.

---

**I6 — ADR-0005 descreve um `SessionStart` hook que nunca foi versionado**

- **Doc diz:** "`.claude/settings.json` com SessionStart hook que injeta `.claude/session-start-context.md` no contexto da sessão" (`:58-59`) e, na §Validação, "SessionStart hook injeta inventário deterministicamente" (`:86`). "hooks" está no título (`:1`) e no índice (`docs/adr/README.md:35`).
- **Código faz:** `.claude/settings.json` contém só `{"$schema": ...}`; `.claude/session-start-context.md` não existe. **Precisão do verificador:** não é "deixou de existir" — `.claude/` só entrou no versionamento em `4d3e1fbf` (2026-05-31, 13 dias depois do ADR) e esse primeiro estado já não tinha `hooks`. `git log --all -S "SessionStart"` retorna só `603f55da`, o commit que **adicionou o texto do ADR**. O único registro de que existiu é o diário de 2026-05-18 (`:50`, `:101`), fora do git.
- **Severidade:** rebaixada de "engana-quem-lê" — o resultado prático prometido (inventário no contexto) é entregue pela outra rota que o próprio ADR lista e que existe (`CLAUDE.md` auto-carregado → `AGENTS.md`); 0 referências ao hook fora do ADR. Escopo meta-infra do repo, sem efeito sobre formato, codec ou API.
- **Correção:** marcar `:58-59` e `:86` como não vigentes, apontando a rota real; alinhar `:1` e `docs/adr/README.md:35`, que ainda anunciam "hooks".

---

### 2.3 COSMÉTICO (4)

---

**C1 — ADR-0025/0026 documentam `#TCF.7 M` e prometem `fallback=False` → `#TCF.6 M` "byte-idêntico ao legado"; os dois magics foram cortados**

- **Doc:** `docs/adr/0025-...:34,47`; `docs/adr/0026-...:29,44`
- **Código:** `src/tcf/multi/core.py:292-296`; `src/tcf/decoder.py:136-142`. Rodado pelo auditor: `encode(t, fallback=False)` → `#TCF.8M13=n,cat`.
- **Precisão do verificador:** `fallback=False` hoje não produz "o legado com outro magic" — produz um wire `.8` inteiro (magic `#TCF.8M`, meta INLINE, sizes em hex), 104 B contra 68 B do default, RT OK. A promessa "byte-idêntico ao legado" falha em mais do que o magic.
- **Correção:** nota de topo em 0025/0026 no formato de `0017:13-18` ("Corpo imutável — só esta nota"), + `docs/adr/README.md:55-56`, + back-link em `0032` §"Relation to other ADRs" (hoje ausente).

---

**C2 — `src/tcf/multi/core.py:422` repete a afirmação do legado cortado.** Mesma raiz de C1 e de E8; comentário interno, sem consumidor externo.

---

**C3 — `docs/algorithms/TCF-format.pt-BR.md:70-71` e `:76` duplicam a linha do version-stamp na mesma tabela.** Confirmado por leitura. Corrigir junto com E3, custo zero.

---

**C4 — ADR-0022: o flip de `fallback` (False → True, 2026-06-14, `2b34248f`/`d8b537a5`) não está registrado em ADR nenhum, e produz contradição de três vias dentro de `docs/adr/`:** `0022:33,:89` (False, flip PENDENTE) × `0024:74` (ainda PENDENTE, no **mesmo dia** do flip) × `0025:34`/`0026:29` (default True, atribuindo o flip ao 0024 que o deixa pendente). Doc viva já diz `True` (`encode-knobs.md:28`, `multi/core.py:292-293`, `STATUS.md:424`), e seguir a instrução do 0022 (`fallback=True`) é no-op correto — por isso é resíduo de registro, não erro de uso. Correção = a linha `docs/adr/README.md:52`.

---

## 3. O PADRÃO

Nomear a forma vale mais que a lista. Cinco padrões, um contra-padrão.

**P1 — A convenção de imutabilidade tem uma válvula, e a válvula está fechada.**
`docs/adr/README.md:8-11` proíbe editar ADR aceito e manda registrar mudança de vigência (a) num ADR novo com back-link, ou (b) no campo Status do índice. Os welds recentes foram para **código + `STATUS.md` + ticket** e nunca para o índice. Resultado: 7 dos 14 achados são a mesma falha — `docs/adr/README.md` deixou de ser mapa de vigência (E4, E7, I1, I3, I4, C1, C4). Ele é o único artefato editável por convenção e é o que ninguém editou. **Corolário operacional:** metade do trabalho de conserto é uma passada numa tabela de 7 linhas.

**P2 — Default virado, ADR preso no opt-in.**
Dois knobs (`fallback`, `min_header`) nasceram opt-in "para preservar byte-canonical" e viraram default em 14/06. A doc viva acompanhou (`encode-knobs.md:28-29`, `api.md:65`); o ADR e o índice não; e o **enquadramento** de `encode-knobs.md:3-5` ficou preso ao regime antigo mesmo com a tabela certa 25 linhas abaixo. É a variante "doc de release-gate que sobreviveu ao release" do calibre 1 do owner. Casos: E7, I5, C4.

**P3 — Comentário de código é documentação sem gate.**
5 dos 14 achados estão dentro de `src/tcf/` (`decoder.py:5-8`, `:57-60`, `:279-282`; `__init__.py:56-57`; `multi/core.py:422`). Nenhum teste os cobre. Em pelo menos um caso (`fe939eef`) o edit que mudou o comportamento e o comentário que ficou errado estavam **no mesmo hunk**. `src/tcf/__init__.py` chega a enunciar o gate — "o TESTE mede, a prosa aponta" — como frase, e não como teste; e a linha imediatamente seguinte é justamente a que aponta para o número errado (E9).

**P4 — Literal copiado de pin, que não se re-deriva.**
1586 → 1545 (e o ratio derivado 53.2% → 51.8%); 11 B → 7 B; "12 colunas de data (10 distintas)" do calibre 3 do owner. Em todos, o **pin no teste está certo** e a cópia na prosa apodreceu. Bate literalmente com a diretriz já registrada no projeto ("números vivem nos TESTES — NÃO copiar aqui"). A distinção que importa: um número **medido** e um número **derivado** (ratio) apodrecem em par, e o derivado costuma passar despercebido.

**P5 — Snapshot datado lido no presente — e o critério que separa.**
O calibre 1 do owner (`tcf8h-header-checklist.md`, "nada disto está weldado") e a superfície de notas de lab inteira. O critério que a verificação adversarial estabeleceu, e que derrubou 3 das 5 rejeições:

> Um registro datado que se declara datado **não é defasagem**. Ele vira defasagem quando (a) outro doc vivo o aponta como estado corrente, (b) ele afirma no **presente** ("continua válido", "hoje", "está implementado"), ou (c) o mesmo enunciado ecoa num doc de referência viva.

Foi assim que ADR-0030 (pins 1523/303/89616) sobreviveu — o próprio doc diz "pré-1.0 baselines re-pináveis" 12 linhas abaixo — e foi assim que `0034:5-6` ("continua válido", presente) virou o alvo legítimo em I2 no lugar da tabela de `0029:77-83`.

**Contra-padrão — a direção inversa existe, e apareceu uma vez.**
No caso do delimitador de polaridade (ADR-0035), era o **código atrás do doc**: o pré-passe rodava numa rota (`.8M`) que o ADR já excluía em `:4-5` e `:122`. O fix não exigiu emenda de doc — alinhou o código ao escopo já declarado. Consequência para a hipótese do owner: "as revisões deixaram coisa pra trás" está certo, mas a direção da defasagem não é única, e a triagem precisa checar as duas.

---

## 4. O que está ALINHADO (não re-auditar)

**Superfícies varridas e conferidas, com resultado limpo:**

- **Suíte inteira** no estado atual: 1285 passed / 3 skipped, batendo com `STATUS.md:78`. Nenhum achado desta auditoria corresponde a bug de codec.
- **Pins dos testes** — todos corretos e re-medidos: `D1_D9_TOTAL = 1545` (`tests/test_regression_v1_baseline.py:96`), `D17A_INVARIANT = 300` (`:101`), `REAL_WORLD_TOTAL = 89430` (`tests/test_real_world_snapshots.py:46`). A medição viva de D1-D9 reproduz pin a pin (125/173/184/120/267/274/222/107/73 = 1545).
- **`docs/reference/encode-knobs.md:28-29,34-35,41-43`** e **`docs/reference/api.md:65`** — knobs `fallback`/`min_header` (defaults `True`) e semântica do `!` raw estão corretos. São a âncora para corrigir E2 e E7.
- **`docs/reference/api.md:1-3,9,17`** — é a fonte declarada da superfície pública e lista `view`/`LazyTCF`/`Filtered` corretamente; `docs/reference/lazy-view.md:20-21` lhes dá contrato de estabilidade. Confirmado: `len(tcf.__all__) == 15`, `'view' in tcf.__all__`.
- **STATUS.md dos tipos** — o auditor da superfície de tipos registra que está atualizado e anotado, **inclusive com a nuance** de que a situação (3) do `T-NATURE-IGNORADA-CALADA` apenas encolheu (não sumiu). O calibre 2 do owner (ticket não riscado) não se repetiu nessa passada.
- **Front-matter `status:` dos 84 tickets** — extraído por script e conferido; 10 lidos integralmente sem divergência de estado.
- **Blocos python executáveis dos docs de usuário** — todos rodados contra `src/`; o único que falha é o do `README` (E6), e falha por uma linha de import.
- **Verificador de links internos** sobre 60 arquivos de `docs/` — sem achado reportado.
- **`docs/adr/0035`** (delimitador de polaridade) — escopo declarado em `:4-5` e `:122` bate com o código pós-fix; varredura dos 12 headers in-scope emitidos pelo encoder: 0 separações indevidas, 0 RT falso. O weld C1 está registrado em `STATUS.md:78`, em `src/tcf/decoder.py:154-163` e no `result.md` §6 do lab.
- **`docs/adr/0030`, `0017`, `0024`, `0028`** — a política de versionamento pré-1.0 (git-as-compat, baselines re-pináveis) está coerente entre si e com os re-pins registrados em `0034:53-54` e `0035:91,93`.

**Reivindicações que NÃO procederam (3 legíveis das 5 nomeadas) — registradas para ninguém re-abrir:**

1. *"ADR-0035 justifica a ausência de escopo"* — o ADR **declara** escopo em `:4-5` e `:122`, e o defeito medido ocorreu fora da gramática que ele escopa. Direção inversa (código atrás do doc).
2. *"ADR-0017 exige nota no ADR para cada export novo; `view`/`LazyTCF`/`Filtered` entraram sem ADR"* — a cláusula citada (`0017:119`) está dentro do regime revogado por `0024:7` e o próprio `0017:14-18` avisa disso; a autoridade da superfície é `api.md:1-3`, que lista os três; e o registro de decisão existe em `tickets/T-CODE-LAZY-VIEW-PROMOTE.md` (closed) + `0028:24` + `0032:60-63`.
3. *"ADR-0030 cita pins 1523/303/89616; hoje são 1545/300/89430"* — o próprio ADR declara os pins re-pináveis pré-1.0 (`:43-47`), nomeia os **arquivos** como referente primário (`:29-31`), e editá-lo seria proibido por `docs/adr/README.md:9-10`. Os três re-pins estão registrados em ADR novo (`0034:53-54`, `0035:91,93`), exatamente como a convenção manda.

---

## 5. O que NÃO foi coberto (honestamente)

**5.1 — Lacuna no próprio pacote entregue a esta síntese.**
O relatório recebido **nomeia 23 defasagens confirmadas e 5 não-procedentes**; o payload entregue truncou e trouxe **14 confirmadas legíveis** (a 14ª — `README`/`tcf_lazy` — cortada no meio do campo `confianca`) e **3 não-procedentes**. Portanto **9 confirmadas e 2 rejeições não estão neste mapa** e permanecem sem endereço. Elas existem no output dos auditores e devem ser recuperadas antes de qualquer conserto — sob o critério de conserto da §6, uma delas pode estar acima de E1. Este é o item mais importante desta seção.

**5.2 — Aritmética do funil, para calibrar confiança.**
6 auditores leram **233 documentos** (49 ADRs+índice / 28 doc pública / 21 notas H+view / 29 notas de tipos+tickets / 92 STATUS+tickets+docstrings / 14 módulos na varredura inversa) e levantaram **97 reivindicações**. Chegaram a esta síntese 23 confirmadas + 5 rejeitadas = 28. As ~69 restantes não vieram nem como confirmadas nem como rejeitadas — não sei se foram deduplicadas entre superfícies, fundidas em itens compostos, ou perdidas. Não trato a taxa 23/97 como medida de qualidade dos auditores; trato como sinal de que o funil não é auditável a partir do que recebi.

**5.3 — Superfícies declaradas fora de escopo pelos próprios auditores:**

- **Notas de tipos/bN/single-col da segunda metade da cronologia** — o auditor de `.8H`/view declara explicitamente que não as auditou.
- **`docs/adr/` na varredura de tipos** — só `0036` e `0041` foram lidos, e como prova pontual.
- **`docs/how-to/` e `docs/tutorials/`** — cobertos apenas pela superfície de doc pública (encode-csv-file, inspect-compression, use-natures, getting-started EN+pt-BR); a superfície de tipos os declara fora.
- **READMEs dos labs** — usados só como evidência pontual, nunca auditados como documento.
- **`docs/archive/`** — excluído por desenho.
- **`docs/theory/`** — só `docs/theory/strategies/` foi tocado.
- **Notas de lab de 2026-05/ e 2026-06/** — varridas por grep (`hierarq|.8H|DatasetH|view|lazy|H-QUERY|LazyTCF`), 61 arquivos casaram, **21 lidos**. Os 40 restantes não foram abertos.

**5.4 — Não auditado por ninguém, e vale registrar:** os 3 wire-formats emitidos pela rota tipada (`b`/`n`/`s`) não têm ADR próprio (ver I2) — não é defasagem de doc existente, é ausência de doc. E `experiments/lab/dirty/notas/` como corpo (centenas de arquivos) foi amostrado, não varrido: o padrão P5 sugere que a taxa de snapshot-lido-no-presente lá é maior que nas outras superfícies, mas isso é **suspeita**, não achado — não tenho o inventário.

---

## 6. Ordem de conserto — NADA a consertar agora

> O owner pediu **estudo antes de código**. As ondas abaixo são a ordem proposta, não uma fila de execução. Nenhuma edição foi feita nesta auditoria.

**Critério, em três eixos, aplicados nesta ordem:**

1. **Custo de errar para quem porta o formato a partir do doc:** perda silenciosa de dado > wire inválido emitido > wire válido rejeitado > canonicidade quebrada (RT por valor passa, gate byte-exato falha) > exemplo que não roda > número errado citado.
2. **Natureza do doc:** vivo (`docs/reference/`, `docs/algorithms/`, `README*`, `docs/vocabulary.md`) = editável in-loco, custo de 1 linha. Registro datado (ADR aceito) = imutável, exige ADR novo — mais caro, portanto **em lote**.
3. **Se a correção fecha uma classe ou um caso:** uma passada em `docs/adr/README.md` fecha 7 itens; um teste de prosa fecharia P3+P4 permanentemente.

---

**Onda 0 — decisão de política (é o que o owner pediu, e é a única coisa a fazer agora).**
Duas perguntas, ambas de resposta do owner, ambas bloqueando as ondas seguintes:

- (a) **`docs/adr/README.md` é campo mantido de vigência?** A evidência diz que sim (`:43`, `:47`, `:54` já carregam notas de supersessão). Se sim, I1 sozinho fecha 7 dos 14 itens e as ondas 3-4 encolhem para uma tabela.
- (b) **Recuperar as 9 confirmadas + 2 rejeições faltantes** (§5.1) antes de fixar a fila. É barato (o output dos auditores existe) e pode reordenar a onda 1.

---

**Onda 1 — docs vivos, edição in-loco, 9 arquivos.** Ordenada por eixo 1:

| # | Arquivo:linha | Item |
|---|---|---|
| 1 | `docs/algorithms/output-convention.md:71-83` | E1 — perda de dado |
| 2 | `docs/vocabulary.md:46` | E2 — wire inválido |
| 3 | `docs/algorithms/TCF-format.pt-BR.md:64-78` + `.en.md:60-72` | E3 — wire válido rejeitado (+C3 de graça) |
| 4 | `docs/algorithms/TCF-format.pt-BR.md:86-87` + `.en.md:80-81` | E4 — contrato de erro divergente |
| 5 | `docs/reference/api.md:57` + `docs/reference/json-equivalence.md:71` | E5 — canonicidade |
| 6 | `README.md:449` + `README.pt-BR.md:454` | E6 — 1 linha de import, 2 arquivos |
| 7 | `docs/reference/encode-knobs.md:3-5` | I5 — enquadramento |

Nenhuma toca `src/`. Nenhuma toca ADR. Todas as substituições literais estão na §2.

---

**Onda 2 — prosa dentro de `src/tcf/`, 3 arquivos, 5 pontos** (E8 a/b/c, E9, C2). Zero risco de formato — são comentários e docstrings — mas exigem a disciplina de tocar **só** a prosa. Se um teste de prosa for adotado (ver onda 5), esta onda é o insumo dele.

---

**Onda 3 — um ADR único de reconciliação.** Em vez de um ADR por item, um ADR que supersede em lote o que os welds de junho-julho revogaram, com back-links: forward-compat de nature (0027, BUG-13b/T-QA-8), cláusula do skip de brackets (0006), defaults de `fallback`/`min_header` (0022/0023), magic `#TCF.7`/`#TCF.6` (0025/0026), extensão do discriminador para `b`/`n`/`s` (lacuna de I2 — este é o único que registra decisão **nova**, não supersessão), e canonicidade de `[]` (0033). Custo de um ADR contra sete; e a §"Relation to other ADRs" do 0032 ganha os back-links de 0025/0026 que hoje faltam.

---

**Onda 4 — a tabela de Status do índice** (I1: `docs/adr/README.md:35,36,52,53,55-56,57,61`) + stamps em `0031:3`, `0032:5`, `0023:3`, `0006` (I3, I4). Depende da onda 3 para ter o número do ADR de reconciliação a citar. Se a onda 0(a) responder "não, o índice não é campo de vigência", esta onda vira outra coisa e a política precisa ser escrita em `docs/adr/README.md` antes.

---

**Onda 5 — cosmético e estrutural, opcional:** C1 (notas de topo em 0025/0026), C2, I6 (ADR-0005 + título + índice). E a decisão estrutural que P3+P4 pedem: um gate que faça a prosa apontar para o pin em vez de copiá-lo (o enunciado já existe em `src/tcf/__init__.py` como frase). Isso é mudança de processo, não conserto de doc — fora do escopo do que o owner pediu, registrado aqui só porque é a resposta ao padrão, não aos casos.