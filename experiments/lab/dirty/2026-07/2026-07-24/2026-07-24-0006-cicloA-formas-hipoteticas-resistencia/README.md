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

## 2. O que vale contra o TCF de hoje

| dataset | TCF hoje (`.8H`) | F6 hipotético | Δ |
|---|---:|---:|---:|
| bool | 41 B | 25 B | **−16 B** |
| int | 36 B | 20 B | **−16 B** |
| float | 43 B | 27 B | **−16 B** |
| **string** | **16 B** | 24 B | **+8 B** ⚠️ |

- **Tipados**: hoje o TCF embrulha bool/int/float no `.8H` (`#V\z#:N[]:…`) **só para preservar o
  tipo** — o envelope inteiro vira 1 char de tag. ~15 B por coluna.
- **⚠️ String PIORA**: hoje já é órfã com **header 0 B**. Escrever `#TCF.8s` custa 8 B para declarar o
  que já era dedutível. ⇒ **a forma tipada só vale para tipos NÃO-string**; string permanece órfã.
  Confirma a regra de implicitude do primeiro estudo — e é o tipo de coisa que só aparece medindo.

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
