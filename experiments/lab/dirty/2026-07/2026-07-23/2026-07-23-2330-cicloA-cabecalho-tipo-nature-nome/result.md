# Ciclo A — cabeçalho single-col: tipo × nature × nome

Protocolo `cicloA-v2` (matriz declarada em MANIFESTO.md ANTES de medir). BODY CONGELADO; só a moldura varia. `order_free` fora (adiado .9).

## Resumo por gramática

`hijack` = **teste decisivo**: o parser aceita uma forma EXISTENTE (`#TCF.8M/H/espaço/\n`) como header tipado. Qualquer valor > 0 **refuta** o candidato — ele sequestra rotas do formato.

| gramática | aplicáveis | pass | fail | N/A | **hijack** | rota confundida | malformados rejeitados | header mín (B) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G1-slot-unico | 55 | 0 | 55 | 55 | **0** | 0 | 9/9 | 9 |
| G2-eixos-separados | 88 | 88 | 0 | 22 | **0** | 0 | 8/9 | 8 |
| G3-tag-colada | 88 | 44 | 44 | 22 | **2** | 44 | 4/9 | 7 |
| G4-sem-assinatura | 88 | 88 | 0 | 22 | **0** | 0 | 8/9 | 2 |

**Detalhe dos hijacks:**

- `G1-slot-unico`: —
- `G2-eixos-separados`: —
- `G3-tag-colada`: '#TCF.8M'->tipo='M'; '#TCF.8H'->tipo='H'
- `G4-sem-assinatura`: —

## Headers representativos (tipo=b, nature=cpf, nome=idade)
```
G1-slot-unico: N/A — G1 tem UM slot: tipo e nature não cabem juntos
G2-eixos-separados: '#TCF.8:b idade:cpf'  (18 B)
  '#' 'T' 'C' 'F' '.' '8' ':' 'b' ' ' 'i' 'd' 'a' 'd' 'e' ':' 'c' 'p' 'f'
G3-tag-colada: '#TCF.8b idade:cpf'  (17 B)
  '#' 'T' 'C' 'F' '.' '8' 'b' ' ' 'i' 'd' 'a' 'd' 'e' ':' 'c' 'p' 'f'
G4-sem-assinatura: ':b idade:cpf'  (12 B)
  ':' 'b' ' ' 'i' 'd' 'a' 'd' 'e' ':' 'c' 'p' 'f'
```

## Leitura

- **G1 (slot único) — REFUTADA**: 55 células N/A porque tipo e nature NÃO CABEM JUNTOS num só slot; e quando só um cabe, o parser não sabe se o `{id}` é tipo ou nature (`AMBIGUO(slot unico)`). É exatamente a colisão tipo↔nature que o owner pediu pra ver. (Na v1 ela aparecia também com 33 'colisões' — era FALSO POSITIVO: G1 estende legitimamente a forma-espaço. A v2 separa extensão de colisão.)
- **G3 (tag colada) — REFUTADA pelo teste decisivo**: `hijack=2` — o parser aceita as formas existentes como se fossem tipos (`#TCF.8M`→`tipo='M'`, `#TCF.8H`→`tipo='H'`). Pôr TIPO no índice 6 **sequestra o Eixo-1** (estrutura). Confirma a hipótese do manifesto — e só ficou visível com as tags adversariais `M`/`H` da v2.
- **G2 (eixos separados) — ÚNICA candidata que sobrevive**: 88/88 recuperam a tripla (nome, tipo, nature), `hijack=0`, 0 rotas confundidas. Tipo no discriminador `:`, nature no sufixo — namespaces distinguíveis (§S1.6). Custo: 8 B no caso com nome+nature.
- **G4 (sem assinatura)**: header mínimo (2 B) e `hijack=0`, mas **não identificável externamente** — perde §S1.1 (autocontenção) e §S1.7 (inspeção). Fica como PISO de comparação de bytes, não como candidata.
- **REQUISITO descoberto pelo lab (§S1.5 fail-loud)**: G2 é estruturalmente sã (`hijack=0`) mas aceita `#TCF.8:b\` como `tipo='b\'` — o escaping é validado no NOME, não na TAG. ⇒ a tag de tipo precisa de **namespace FECHADO (whitelist)**, não texto livre. É o único malformado que G2 aceita, e vira requisito da gramática, não detalhe de implementação.
- **Resposta à pergunta do owner (tipo × spec × nome)**: com **eixos separados**, um nome igual a uma tag de tipo (`b`) ou a um id de nature (`cpf`) **deixa de ser problema** — cada campo vive num namespace próprio e o escaping + split no último `:` não-escapado resolve nomes com `:`/espaço/`\`/`\n`. O conflito só existe quando os eixos são compartilhados (G1) ou quando o tipo invade o eixo de estrutura (G3).
- **Nome adversarial**: o escaping de `:`/`\`/`\n` + split no ÚLTIMO `:` não-escapado (convenção do multi-col real) sustenta nome `a:b`, `M`, `H`, `b` e `cpf` sem colisão nas gramáticas de eixos separados. **Nome igual a tag de tipo ou a id de nature deixa de ser problema quando os eixos são separados** — é o achado central pra pergunta do owner.

**440 células · 99 fail · 121 N/A · malformados: 29/36 rejeitados.** Artefatos: `intermediates/00-matrix.csv`, `01-cases.json`, `02-header-breakdown.txt`, `outputs/01-malformed-results.json`. Regenera: `python run.py`.