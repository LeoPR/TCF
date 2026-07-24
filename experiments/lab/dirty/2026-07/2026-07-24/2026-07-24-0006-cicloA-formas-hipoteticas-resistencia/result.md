# Ciclo A (cont.) — formas HIPOTÉTICAS: resistência + a tipagem sobrevive?

**Body REAL, header HIPOTÉTICO**: o corpo vem do `src/tcf` (congelado); só a moldura varia. `outputs/` = wire REAL do TCF (âncora). Formas hipotéticas = `intermediates/*.tcfp`.

GATE do owner: *a vantagem em arquivo não faz a tipagem sumir internamente* — o decode tem que devolver o dataset **TIPADO**.

## 1. GATE — a tipagem volta? (body real + moldura implícita)

| dataset | tag | corpo REAL (do src/tcf) | wire hipotético F6 | RT tipado |
|---|---|---|---|:---:|
| `D-bool` | `b` | `'true\nfalse\n*2|^1\n'` | `#TCF.8b` | ✅ |
| `D-int` | `n` | `'*3+1|\\1\n\\42\n'` | `#TCF.8n` | ✅ |
| `D-float` | `n` | `'\\1.\\5\n\\2.\\25\n\\3.\\0\n'` | `#TCF.8n` | ✅ |
| `D-str` | `s` | `'ana\nbruno\ncarla\n'` | `#TCF.8s` | ✅ |
| `D-n1` | `b` | `'true\n'` | `#TCF.8b` | ✅ |
| `D-n0` | `b` | `''` | `#TCF.8b` | ✅ |

**Gate: 6/6 ✅.** O tipo viaja como TAG (1 char) e é reconstruído no decode — a moldura encolhe, a semântica NÃO. `D-bool` volta `True/False` (bool), não `'true'/'false'` (string). É a confirmação do alerta do owner.

## 1b. O que vale contra o TCF de HOJE — baseline com `#TCF.8` (corrigida)

> **Correção do owner**: comparar contra o órfão *sem header* era injusto. Os formatos estudados têm no mínimo a declarativa `#TCF.8`; ficar abaixo disso deveria exigir parâmetro explícito. Onde o dado aceita `stamp=True`, a baseline é a estampada.

| dataset | tag | TCF hoje (rota real) | baseline c/ `#TCF.8` | F6 | Δ vs baseline |
|---|---|---:|---:|---:|---:|
| `D-bool` | `b` | .8H (envelope) | 41 B | 25 B | **-16 B** |
| `D-int` | `n` | .8H (envelope) | 36 B | 20 B | **-16 B** |
| `D-float` | `n` | .8H (envelope) | 43 B | 27 B | **-16 B** |
| `D-str` | `s` | órfão (0 B header) | 23 B | 24 B | **+1 B** |
| `D-n1` | `b` | .8H (envelope) | 28 B | 13 B | **-15 B** |

- **Tipados (bool/int/float)**: hoje o TCF embrulha no `.8H` (`#V\z#:N[]:…`) só pra preservar o tipo — e `stamp` nem se aplica (é rota hierárquica). A forma implícita economiza **~15 B por coluna**: o envelope inteiro vira 1 char.
- **String, com baseline JUSTA**: `#TCF.8\n`+corpo = 23 B vs `#TCF.8s\n`+corpo = 24 B ⇒ a tag custa **+1 B**, não +8. A conclusão qualitativa se mantém (string é o default implícito, não vale declarar), mas a magnitude era artefato de baseline errada.

## 1c. O VAZIO — `[]` vs `[""]` (sugestão do owner, MEDIDA)

| dataset | wire REAL | bytes | rota | decode | RT |
|---|---|---:|---|---|:---:|
| `[]` | `'#TCF.8H#D0\n'` | 11 | .8H | `[]` | ✅ |
| `[""]` | `'\n'` | 1 | flat/órfão | `['']` | ✅ |
| `["",""]` | `'*2|\n'` | 4 | flat/órfão | `['', '']` | ✅ |

**Canonicidade (§S1.2)**: `'#TCF.8\n'` → `['']` · `'#TCF.8\n\n'` → `['']`

⚠️ **DUAS GRAFIAS, MESMO DATASET** — viola §S1.2 (*um dataset + uma config ⇒ uma única grafia*). Corpo vazio e corpo com uma linha vazia colapsam em `['']`. **Consequência**: a forma flat NÃO CONSEGUE expressar `[]` — por isso `[]` foge pro `#TCF.8H#D0`.

### Reavaliação da sugestão do owner

O owner sugeriu: *quando está vazio não precisa de nada, nem o `b`*; e que `#TCF.8` sem tag (string implícita) com corpo vazio seria `[""]`. **A medição sustenta e refina:**

1. **A tag É dispensável no vazio** — e por motivo mais forte que economia: uma lista vazia **não tem elemento algum**, logo não há tipo a preservar. `[]` de bool e `[]` de int são o MESMO dataset. Declarar `b` ali é escrever informação que não existe.
2. **A ambiguidade intuída é REAL e já está no formato de hoje**, não é hipotética: `#TCF.8\n` e `#TCF.8\n\n` decodificam ambos para `['']`.
3. **Saída natural** (a estudar, não decidida): fixar **0 linhas ⇒ `[]`** e **1 linha vazia ⇒ `[""]`**. Isso (a) restaura a canonicidade, (b) deixa a forma flat expressar `[]` sem o `.8H#D0` — elimina uma rota inteira, e (c) dispensa a tag no vazio, exatamente como o owner propôs.
4. **Custo atual do desvio**: `[]` gasta 11 B via `.8H#D0` onde `#TCF.8\n` (7 B) bastaria — e pior, obriga uma ROTA hierárquica só pra dizer 'nada'.

## 2. Resistência da moldura a variações

| forma | combos | ok | rejeitados | **sequestros do Eixo-1** | nome perdido |
|---|---:|---:|---:|---:|---:|
| `F1 (real) #TCF.8 {nome}:{id}` | 63 | 63 | 0 | 0 | 0 |
| `F2 #TCF.8{nome}:{id}` | 63 | 49 | 14 | 14 | 0 |
| `F4 #TCF.8{nome}` | 63 | 49 | 14 | 14 | 0 |
| `F5 #TCF.8:{id}` | 63 | 12 | 51 | 0 | 0 |
| `F6 #TCF.8{id}` | 63 | 8 | 55 | 2 | 0 |

## 3. Implicitude — o que é ESCRITO vs DEDUZIDO por exclusão

| forma | bytes (tag `b`, sem nome) | rota single-col | presença de nome | tipo |
|---|---:|---|---|---|
| F1 `#TCF.8 :b` | 9 | **escrita** (espaço) | deduzida (vazio) | **escrito** |
| F5 `#TCF.8:b` | 8 | **escrita** (`:`) | deduzida (não há) | **escrito** |
| F6 `#TCF.8b` | 7 | **deduzida por exclusão** | deduzida (não há) | **escrito** |

**F6 é a mais implícita**: a rota single-col é *intuída por exclusão* — não é `M`, não é `H`, não é espaço, não é `\n`, logo é token de tipo. O único campo irredutível escrito é a TAG. É exatamente o 'intuído por exclusão é vantagem'.

⚠️ **Mas F6 e F4 são a mesma forma** (`#TCF.8` + token nu): só é seguro porque a tag vem de namespace FECHADO. Se o token pudesse ser um NOME (aberto), a dedução por exclusão quebra — ver coluna 'sequestros' da §2.

## 4. Leitura

- **A tipagem NÃO some**: o gate da §1 mostra que, com moldura mínima (`#TCF.8b`), o decode devolve bool/int/float corretos. O tipo deixa de ocupar envelope hierárquico e passa a ocupar **1 char**; a semântica é idêntica.
- **F5 e F6 resistem** às variações de id porque não têm onde guardar nome — o que as torna estreitas mas robustas. F2/F4 perdem/deformam nome e sofrem sequestro do Eixo-1 quando o nome começa com `M`/`H`.
- **Custo do nome**: nenhuma forma implícita (F5/F6) carrega nome. Se nome for necessário, é F1 — que a evidência do 2330 mostrou robusta. Isso reforça o par **(1)+(6)**: F1 quando há nome, F6 quando não há.
- **Contra-indicação registrada**: a economia de F6 sobre F1 é de 2 B — relevante só em payload minúsculo, que é justamente o foco declarado do projeto.

---
**Gate de tipagem: 6/6.** Artefatos: `inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `intermediates/*-hipotetico-F6.tcfp` (HIPÓTESE) · `outputs/*-wire-real.tcf` (REAL). Regenera: `python run.py`.
