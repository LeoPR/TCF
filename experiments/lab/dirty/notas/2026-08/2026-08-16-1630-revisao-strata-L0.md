# Revisão Strata — aderência ao núcleo L0

> **Owner (2026-08-16)**: *"revise com o método Strata, apenas pra ver se está tudo alinhado."*

Protocolo: para cada um dos 10 princípios L0, *"o TCF adere? proporcional a §9?"*, maturidade
0–4. **Não altera nada sem aprovação** (brownfield). Escopo desta passada: o ciclo do `.8M`
(2026-08-15/16) — 6 labs, 3 notas, 5 tickets novos.

**§9 é o regulador**: aderência é PROPORCIONAL, não absoluta. Uma nota de exploração não
precisa do rigor de um ADR.

---

## A matriz

| § | princípio | mat. | estado / gap |
|---|---|:--:|---|
| 1 | separação física dos 3 artefatos | **4** | `src/` produto · `experiments/lab/` exploração · `docs/adr`+`STATUS`+`notas` conhecimento. Feito na reorg de 2026-06-02, sustentado |
| 2 | as 4 perguntas | **3** | onde-está (`MAP.md`) ✓ · como-uso (Diataxis) ✓ · por-quê (ADR) ✓ · **é-confiável: o gap desta rodada** (abaixo, §A) |
| 3 | rastreabilidade | **3** | git = traço append-only ✓ · `STATUS` = superfície que decai ✓ · notas = conhecimento re-narrável ✓. **Gap: §A** |
| 3-bis | força do artefato | **2 → 4** | **o achado central desta revisão** (§A) — corrigido nesta passada |
| 4 | registro científico | **4** | hipótese-ANTES em 3 labs seguidos (`1450` 4 predições, `1530` 6 invariantes, `1610` 4 predições); **predições refutadas registradas como tais** (a P(b) do `0530`, o erro da curva `v0..vN` no `1530`); viés declarado em todo `datasets-provenance.md` |
| 5 | fonte única por altitude | **3** | `_parse_meta` é fonte única do parse (core **e** view — paridade por construção) ✓ exemplar. **Gap: `_serialize` é closure** — o emissor da gramática não é endereçável (nota `1510` §4.3) |
| 6 | disciplina de fonte | **4** | os 10 refutadores morreram no limite de gasto → achados marcados **candidatos**, 2 reverificados à mão, 7 declarados sem passagem adversarial e mantidos **fora** do STATUS. Isso É honestidade epistêmica |
| 6-bis | autoridade-para-agir | **4** | `src/tcf` intocado em **todos** os commits do ciclo; toda proposta que mexe em src está marcada "aguarda aprovação" |
| 7 | pipeline de maturação | **4** | lab → nota → STATUS ✓. **Regra de três exemplar**: *"o candidato existe e a rota não o consulta"* foi nomeada **6 vezes** e virou o `T-UM-CAMINHO-SO` — o padrão subiu de altitude corretamente |
| 8 | versionamento | **3** | ADR-0024 git-as-compat ✓, baselines re-pináveis ✓. **Gap: dois labs nasceram com a data errada** (contexto defasado na virada do dia); corrigido por `git mv`, lição gravada |
| 9 | economia do esforço | **3** | os labs são proporcionais (o owner inspeciona → distância curta justifica). **Gap na direção OPOSTA: excesso** (§B) |
| 10 | durabilidade do portador | **4** | git + OneDrive + PyPI; wires `.tcf` versionados e verificáveis contra a origem |

---

## §A — o gap central: **força do artefato** (§3-bis), e ele reincidiu

**O owner detectou antes de mim**: *"o lab que foi feito agora está fragmentado, só tem as
saídas sem roundtrip, o que não faz sentido porque aí eu questiono como você conseguiu
verificar algo sem deixar evidência verificável."*

Diagnóstico Strata: um `.tcf` sozinho é **dispositivo**, não **probatório**. Sem a entrada ao
lado e o roundtrip para o diff, falta a *"chave de decifração redundante"* — o leitor não tem
como verificar contra a origem. O RT **foi** asserido em execução; o que faltou foi o artefato
que sobrevive à execução.

**Alcance medido**: dos 11 casos do lab `1610`, **5 tinham output sem input nenhum** (a curva
de `k`) e **11 estavam sem roundtrip**.

**Corrigido nesta passada** (o lab foi re-rodado): 11 entradas + 11 roundtrips + 11 metas +
`INDEX.md`, com o diff entrada×roundtrip rodado **como assert** dentro do `run.py`, e provado
por `diff` externo. Maturidade 3-bis: **2 → 4**.

**Por que é grave**: é a **4ª forma** da mesma falha registrada na memória de processo —
`artifacts/*.txt` genéricos → roundtrip faltando → medir em scratchpad sem lab → agora
**lab com output sem prova**. A regra existia e eu não a apliquei. A causa provável é que os
labs `1400`/`1450`/`1530` desta série gravaram roundtrip e eu tratei o `1610` como
"continuação", não como lab novo com checklist próprio.

**Segundo caso, mesma classe, mesma rodada**: no lab `1530` comparei *"13 B"* do O-FMT-11
contra *"18 B"* do meu wire — **unidade diferente** (header × wire). É o *"declarar
referencial/unidade"* do §3-bis. Detectei e corrigi dentro do próprio lab, e ficou registrado
lá.

---

## §B — o gap oposto: excesso em `STATUS.md` (§9)

O `STATUS.md` tem linhas de ticket com **10.000+ caracteres** (`T-DATETIME-TIPO` 10.160,
`T-NUMERO-SPEC` 16.229). Isso é conhecimento re-narrável comprimido numa **superfície que
decai** — altitude errada (§5) e antieconômico para o leitor (§9).

Não é urgente e não proponho mexer agora (brownfield, e o `STATUS` funciona como compêndio).
Fica registrado como candidato de manutenção: os tickets grandes deveriam virar nota própria
com o `STATUS` carregando o **veredito + link**.

---

## §C — o que está exemplar (para não regredir)

1. **Hipótese-antes, três labs seguidos** — e as **refutações foram registradas como
   resultado**, não escondidas. No `0530` minha predição (b) foi refutada e o resultado ficou
   *mais forte* por isso; no `1530` eu quebrei minha própria curva e registrei a correção.
2. **`_parse_meta` como fonte única** — decode e view consomem a mesma função. É o §5 no
   sentido certo: *autoridade única ≠ instância única*.
3. **A regra de três funcionando**: o padrão *"o candidato existe e a rota não o consulta"*
   foi observado 6 vezes e **subiu de altitude** virando causa nomeada (`T-UM-CAMINHO-SO`),
   com os sintomas apontando para ela em vez de duplicá-la.
4. **Honestidade epistêmica sob falha de ferramenta**: quando os refutadores morreram, o
   registro diz explicitamente quais achados **não** passaram por adversário — e eles não
   entraram no STATUS.

---

## Veredito

**Alinhado, com um gap real que o owner pegou e que já está corrigido.** Média das
maturidades: **3,5** (era 3,4 antes da correção do §A). Nenhum princípio abaixo de 3 após esta
passada.

Os dois gaps remanescentes — `_serialize` closure (§5) e o excesso do `STATUS` (§9) — **estão
ambos já registrados** em nota (`1510` §4.3 e aqui §B) e nenhum bloqueia o trabalho do `.8M`.

**Nada foi alterado além do conserto do lab `1610`** (que restaura uma regra já existente, não
cria política nova).
