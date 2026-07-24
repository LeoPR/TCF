# 2026-07-23-2330 — Ciclo A: cabeçalho single-col (tipo × nature × nome)

Primeiro ciclo do [plano de revisão integral do `.8`](../../../notas/2026-06/tcf8-estrutura-plano.md)
(§5 S1). Matriz **declarada antes de medir** em [`MANIFESTO.md`](MANIFESTO.md) (protocolo `cicloA-v2`).

**Pergunta focal**: qual é a menor moldura canônica que declara só o que o body não deduz — e **como
TIPO, NATURE/spec e NOME de coluna coexistem sem ambiguidade** (a pergunta do owner)?

**Escopo**: BODY CONGELADO (só a moldura varia) · `order_free` FORA ([adiado `.9`](../../../notas/2026-07/2026-07-23-2324-order-free-e-ordenacao-adiado-09.md))
· nada em `src/tcf/`.

## Resultado (440 células)

| gramática | pass | fail | N/A | **hijack** | rotas confundidas | header mín |
|---|---:|---:|---:|---:|---:|---:|
| G1 slot único (`#TCF.8 {nome}:{id}`) | 0 | 55 | 55 | 0 | 0 | 9 B |
| **G2 eixos separados** (`#TCF.8:{tipo} {nome}:{nature}`) | **88** | **0** | 22 | **0** | **0** | 8 B |
| G3 tag colada (`#TCF.8{tipo}`) | 44 | 44 | 22 | **2** | 44 | 7 B |
| G4 sem assinatura (`:{tipo}`) | 88 | 0 | 22 | 0 | 0 | 2 B |

`hijack` = teste decisivo: o parser aceita uma forma EXISTENTE do `.8` como header tipado.

## Conclusões

- **G1 REFUTADA** — tipo e nature não cabem num slot só (55 N/A); quando um cabe, o parser não sabe
  qual é (`AMBIGUO(slot único)`). É a colisão tipo↔nature materializada.
- **G3 REFUTADA** — `hijack=2`: o parser engole `#TCF.8M`→`tipo='M'` e `#TCF.8H`→`tipo='H'`. Pôr TIPO
  no índice 6 **sequestra o Eixo-1 (estrutura)**. Confirma a hipótese do manifesto.
- **G2 é a única que sobrevive** — 88/88 recupera a tripla (nome, tipo, nature), `hijack=0`, 0 rotas
  confundidas. Tipo no discriminador `:`, nature no sufixo: **namespaces distinguíveis** (§S1.6).
- **G4** passa mecanicamente mas **não é identificável externamente** — piso de bytes, não candidata.

### Resposta à pergunta do owner

Com **eixos separados**, um nome de coluna igual a uma **tag de tipo** (`b`) ou a um **id de nature**
(`cpf`) **deixa de ser problema**: cada campo vive em namespace próprio, e escaping + split no último
`:` não-escapado sustenta nomes com `:`/espaço/`\`/`\n`/`M`/`H`. O conflito só aparece quando os eixos
são **compartilhados** (G1) ou quando o tipo **invade** o eixo de estrutura (G3).

### Requisito descoberto (§S1.5)

G2 é estruturalmente sã mas aceita `#TCF.8:b\` como `tipo='b\'` — o escaping é validado no *nome*, não
na *tag*. ⇒ **a tag de tipo precisa de namespace FECHADO (whitelist)**, não texto livre. Vira requisito
da gramática, não detalhe de implementação.

## Emenda `cicloA-v2` (declarada, não silenciosa)

A rodada v1 expôs falha **na própria matriz**: (a) testava colisão na direção errada (header→forma, em
vez de parser→forma), deixando G3 com "0 colisões" enquanto sequestrava rotas; (b) falso positivo em G1
(extensão da forma-espaço lida como colisão); (c) faltavam tags adversariais `M`/`H`. Correções e
justificativa no [`MANIFESTO.md`](MANIFESTO.md#cicloa-v2--emenda-declarada-2026-07-23-após-a-rodada-v1).

## Rodar / artefatos

```
python run.py     # 440 células · regenera tudo deterministicamente
```
`intermediates/00-matrix.csv` (toda célula: pass/fail/N-A) · `01-cases.json` (matriz + protocolo) ·
`02-header-breakdown.txt` (header byte a byte) · `outputs/01-malformed-results.json` (aceitação/rejeição)
· `result.md`.

**Não conclui o cabeçalho** — entrega a tabela propriedades × wire. Faltam os critérios de julgamento
(§S1.7 inspeção, §S1.9 streaming, §S1.10 paridade S/M/H) e o custo em contexto de body real.
