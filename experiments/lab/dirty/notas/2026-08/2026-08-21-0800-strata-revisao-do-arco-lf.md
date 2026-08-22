# 2026-08-21 — revisão Strata (L0) do arco do `\n` final

Pedido do owner: *"me parece mais simples do que tudo que foi feito, só temos que lembrar disso
pra deixar bem documentado. use o Strata pra revisar isso também, precisamos de rastreabilidade
para poder colocar em documentação no futuro."*

Fonte canônica: `Acadêmicos/Methodologies/recipe/knowledge-architecture.pt-BR.md` (projeto
**Strata**). Protocolo: para cada princípio L0, "o TCF adere? proporcional a §9?", maturidade
0–4, e **nada se altera sem aprovação** (brownfield). Escopo desta revisão: **só o arco do `\n`
final** — não é a auditoria periódica.

---

## O achado, no seu tamanho real

Antes da matriz, o que o owner apontou e que a revisão confirma: **o resultado é uma linha.**

```
[]    ->  '#TCF.8\n'
['']  ->  '#TCF.8\n\n'
```

O LF terminador é o único byte que separa **coluna vazia** de **coluna com um valor vazio**.
Como separador (n−1 LFs), as duas colapsariam no mesmo corpo vazio. Ele carrega **1 bit, só
nesse caso de borda** — pouco, e suficiente.

Quatro labs, três respostas, e o que sobrevive é isto. **É a §7 funcionando**: exploração é
descartável por desenho; o que sobe tem de ser reescrito limpo, não herdar a bagunça.

## Matriz de aderência

| § | princípio | estado | maturidade | gap | ação |
|---|---|---|---|---|---|
| **§1** | separação física dos 3 tipos | exploração em `experiments/lab/dirty/`, conhecimento em `docs/`, produto em `src/` | **4** | — | — |
| **§2** | as 4 perguntas | "onde está X" resolvido por `MAP`+`STATUS`; "por que decidiu" pelo ADR/labs | **3** | o achado só era achável entrando pelo lab | teste nomeado (abaixo) o torna achável pelo código |
| **§3** | rastreabilidade (fonte+rationale+versão) | traço append-only preservado; superfície rebaixada com banners | **3 → 4** | **cadeia quebrada**: `0400` apontava para `0500`, que foi **revogado** — quem entrava pelo `0400` caía em leitura morta | **CORRIGIDO**: `0400` → `0700` |
| **§3** | identidade estável da fonte | — | **2 → 4** | a memória do Strata apontava para `knowledge-architecture.md`, que **não existe mais** (virou `.pt-BR.md`) | **CORRIGIDO** na memória |
| **§3-bis** | força do artefato | o achado é **probatório** (par de valores conferível), não dispositivo | **4** | — | — |
| **§4** | registro científico | hipótese declarada em cada lab; resultado honesto (inclusive as duas voltas erradas mantidas) | **4** | — | refutação preservada é conhecimento — os labs errados **ficam** |
| **§5** | fonte única por altitude | **como**=código · **exemplo**=teste · **porque**=prosa | **2 → 4** | os dois wires estavam pinados **separados**; a **relação** — que é o achado — não estava em altitude nenhuma | **CORRIGIDO**: teste `test_o_LF_terminador_e_o_que_distingue_vazia_de_um_vazio` |
| **§6** | disciplina de fonte | primário (execução no repo) sobre secundário; `file`/POSIX verificados e demarcados | **4** | — | — |
| **§6-bis** | autoridade para agir | nada soldado sem aprovação explícita; ADR-0045 §3 foi decisão de **não fazer** | **4** | — | — |
| **§7** | pipeline de maturação | exploração (4 labs) → resultado (0700) → decisão (H-15-08 fechado) | **3** | o resultado maduro ainda **vive dentro do lab**; a narrativa não foi reescrita limpa | ver "o que falta" |
| **§8** | versionamento | 1 commit por achado, mensagem com rationale; história recuperável | **4** | — | — |
| **§9** | economia do esforço | **regulador** | **2** | 4 labs, ~1 200 linhas de registro para um achado de 1 linha | ver abaixo — é o gap real |
| **§10** | durabilidade do portador | git + OneDrive; evidência versionada | **3** | — | fora de escopo |

## O gap que importa é o §9, e ele é meu

**§9 é o regulador**: aderência é proporcional. Produzi **quatro labs** (`0400`, `0500`, `0600`,
`0700`) e ~1 200 linhas de registro para um achado que cabe em **duas linhas de wire**. Três dos
quatro existem porque eu errei — e errei **por não ter procurado o caso de borda primeiro**.

O `0700` levou 10 minutos e resolveu. Se eu tivesse começado perguntando *"qual é o menor par de
datasets que o LF distingue?"*, os labs `0500` e `0600` não existiriam.

**Isso não é desperdício a apagar** (§3: refutação é conhecimento, o traço fica). É **sinal de
processo**: a exploração custou 4× o necessário porque a pergunta certa só apareceu quando o
owner a fez.

## A regra de três (§7) — este achado **não** deve subir mais

O Strata é explícito: *"Não formalize o que aconteceu uma vez"*, e *"tarefa única, sem evolução,
vive legitimamente só no nível de exploração: não consolidar é o comportamento certo, não
preguiça."*

O achado do `\n` **ocorreu uma vez**. Portanto:

- ✅ **resultado** — o lab `0700`, imutável e reproduzível. **Está certo.**
- ✅ **decisão** — `H-15-08` fechado no registry, com rationale. **Está certo.**
- ✅ **exemplo** (§5) — o teste que pina o par. **Feito nesta revisão.**
- ✅ **porque** (§5) — `output-convention.md` §3. **Já existe.**
- ❌ **consolidação/narrativa** — **não fazer.** Não há N≥3 achados sobre o mesmo tema; criar um
  ADR ou um documento próprio para isto seria formalizar N=1, que é exatamente o que a §7 proíbe.

**Ou seja: a documentação futura que o owner quer já tem seus dois portadores certos** — o teste
(exemplo) e a `output-convention.md` §3 (porque). O que faltava era a **relação** pinada, e ela
agora está.

## Rastreabilidade — a cadeia, para citar no futuro

Quem for escrever documentação sobre isto deve citar, nesta ordem:

| altitude | portador | o que carrega |
|---|---|---|
| **porque** | `docs/algorithms/output-convention.md` §3 | a regra em prosa, com o texto antigo (errado) citado |
| **exemplo** | `tests/test_core_rt.py::test_o_LF_terminador_e_o_que_distingue_vazia_de_um_vazio` | o par `[]`/`[""]`, executável |
| **como** | `src/tcf/composicional/syntax.py` (corpo/`split_lf_body`) | a implementação |
| **resultado** | `experiments/.../2026-08-21-0700-lf-a-resposta/` | o achado fechado + evidência |
| **traço** | labs `0400` (argumento errado), `0500` (**revogado**), `0600` (desvio: cabeçalho) | como se chegou lá — e os erros |
| **decisão** | `H-15-08` em `notas/2026-05/roadmap-hipoteses.md` | fechado, com rationale |

**Cadeia de supersedência** (§3), agora íntegra:

```
0400 (conclusão certa, argumento errado)  ──corrigido por──>  0700
0500 (conclusão ERRADA)                   ──revogado por───>  0700
0600 (desvio: cabeçalho)                  ──outro assunto──>  H-15-09
```

## O que NÃO foi verificado (§6: demarcar a ignorância)

- Esta revisão cobre **só o arco do `\n`**. A auditoria periódica L0 do TCF inteiro (60–90 dias)
  **não** foi feita aqui — a última é de 2026-06-18.
- A Parte II (L1) e Parte III (L2) do Strata não foram revisadas: o pedido era rastreabilidade,
  que é L0 §3.
- Não conferi se outros achados do projeto têm o mesmo gap de §5 (fato pinado só em prosa).
  Se o padrão se repetir, **aí** vira consolidação (regra de três).

## Ações desta revisão

| ação | § | estado |
|---|---|---|
| Teste pinando o par `[]`/`[""]` e o **porquê** | §5, §2 | ✅ feito (suíte 1307 → **1308**) |
| Cadeia `0400` → `0700` (era `0400` → revogado) | §3 | ✅ feito |
| Caminho da fonte Strata na memória (`.pt-BR.md`) | §3 | ✅ feito |
| **Não** criar ADR/consolidação para N=1 | §7, §9 | ✅ decisão registrada aqui |
