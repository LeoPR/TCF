# 2026-07-24-0006 — Ciclo A (cont.): formas HIPOTÉTICAS, resistência e o gate da tipagem

Continua [`2026-07-23-2330`](../../2026-07-23/2026-07-23-2330-cicloA-cabecalho-tipo-nature-nome/)
(que mediu o que o TCF emite HOJE). Aqui testamos as formas que **não existem**, contra variações.

**Gate do owner**: *"a vantagem em arquivo não significa que as tipagens internamente somem"* — a
economia é de **moldura**, nunca de **semântica**. O `decode` tem que devolver o dataset **tipado**.

**Desenho**: **body REAL, header HIPOTÉTICO** — o corpo vem do `src/tcf` (congelado, como o manifesto
manda); só a moldura varia. `outputs/` = wire REAL (âncora); formas hipotéticas = `intermediates/*.tcfp`.

## 1. O gate fecha: 6/6 ✅

Com a moldura mínima `#TCF.8b`, o decode devolve `[True, False, True, True]` — **bool**, não
`["true","false",...]`. O tipo sai do envelope hierárquico e passa a ocupar **1 char**. A semântica é
idêntica; só a moldura encolheu.

## 2. O que vale contra o TCF de hoje — **baseline corrigida**

> **Correção do owner**: comparar contra o órfão *sem header* era injusto. Os formatos estudados têm
> no mínimo a declarativa `#TCF.8`; ficar abaixo disso deveria exigir **parâmetro explícito** (hoje é
> o contrário: órfão é default e `stamp=True` é opt-in). Baseline = estampada onde aplicável.

| dataset | rota real hoje | baseline c/ `#TCF.8` | F6 | Δ |
|---|---|---:|---:|---:|
| bool | `.8H` envelope | 41 B | 25 B | **−16 B** |
| int | `.8H` envelope | 36 B | 20 B | **−16 B** |
| float | `.8H` envelope | 43 B | 27 B | **−16 B** |
| string | órfão (0 B header) | 23 B | 24 B | **+1 B** |

- **Tipados**: o `.8H` existe aqui **só para preservar o tipo** — e `stamp` nem se aplica (é rota
  hierárquica). O envelope inteiro vira 1 char: **~15 B por coluna**.
- **String**: com baseline justa a tag custa **+1 B**, não +8. A conclusão qualitativa se mantém
  (string é o default implícito, não vale declarar), mas **a magnitude anterior era artefato de
  baseline errada** — corrigido.

## 2b. O VAZIO — a "sugestão duvidosa" que se confirmou

| dataset | wire real | bytes | rota |
|---|---|---:|---|
| `[]` | `#TCF.8H#D0\n` | 11 | `.8H` |
| `[""]` | `\n` | 1 | flat |
| `["",""]` | `*2\|\n` | 4 | flat |

**Canonicidade quebrada (§S1.2)**: `'#TCF.8\n'` → `['']` e `'#TCF.8\n\n'` → `['']` — **duas grafias,
mesmo dataset**. Consequência: a forma flat **não consegue expressar `[]`**, e por isso `[]` foge para
`#TCF.8H#D0` (11 B) — uma rota hierárquica inteira só para dizer "nada".

**A sugestão do owner se sustenta, e por um motivo mais forte que economia**: uma lista vazia **não
tem elemento algum**, logo **não há tipo a preservar** — `[]` de bool e `[]` de int são o mesmo
dataset. Declarar `b` ali é escrever informação que não existe.

**Saída natural** (a estudar, não decidida): fixar **0 linhas ⇒ `[]`** e **1 linha vazia ⇒ `[""]`**.
Restaura a canonicidade, deixa a flat expressar `[]` sem o `.8H#D0`, e dispensa a tag no vazio.

## 3. Resistência a variações (63 combos por forma)

| forma | ok | rejeitados | **sequestros do Eixo-1** | nome perdido |
|---|---:|---:|---:|---:|
| F1 `#TCF.8 {nome}:{id}` (real) | **63** | 0 | **0** | 0 |
| F2 `#TCF.8{nome}:{id}` | 49 | 14 | **14** | 0 |
| F4 `#TCF.8{nome}` | 49 | 14 | **14** | 0 |
| F5 `#TCF.8:{id}` | 12 | 51 | 0 | 0 |
| F6 `#TCF.8{id}` | 8 | 55 | 2 | 0 |

- **F1 é a mais resistente** (63/63, zero sequestro) — e carrega nome.
- **F2/F4 sofrem 14 sequestros** do Eixo-1: quando o nome começa com `M`/`H`, o header vira multi-col
  ou hierárquico. É a fragilidade de expor o índice 6 a **dado do usuário**.
- **F5/F6 são estreitas mas seguras**: rejeitam muito porque não têm onde guardar nome, e **F6 valida
  contra o namespace FECHADO** (rejeita id fora da whitelist e o `M` adversarial).

## 4. Implicitude — escrito vs deduzido por exclusão

| forma | bytes | rota single-col | nome | tipo |
|---|---:|---|---|---|
| F1 `#TCF.8 :b` | 9 | escrita (espaço) | deduzido | escrito |
| F5 `#TCF.8:b` | 8 | escrita (`:`) | deduzido | escrito |
| **F6 `#TCF.8b`** | **7** | **deduzida por exclusão** | deduzido | escrito |

**F6 é a mais implícita**: a rota é *intuída por exclusão* — não é `M`, não é `H`, não é espaço, não é
`\n` ⇒ é token de tipo. Só a TAG é escrita. Mas isso **só é seguro porque a tag vem de namespace
fechado** — se o token pudesse ser um nome (aberto), a dedução quebra (é a diferença (4)↔(6)).

## Conclusão

O par **(1)+(6)** se sustenta na evidência: **F1 quando há nome** (robusta, 63/63) e **F6 quando não
há** (máxima implicitude, −16 B vs o `.8H` atual). Com a ressalva medida: **não aplicar a tipos
string**, onde a forma órfã (header 0 B) já é o ótimo.

**Não conclui a gramática** — falta custo em body grande, paridade S/M/H e os critérios de julgamento.
**Nada em `src/tcf/`.**

## Rodar

```
python run.py     # 6 datasets × gate + 5 formas × 63 combos
```
