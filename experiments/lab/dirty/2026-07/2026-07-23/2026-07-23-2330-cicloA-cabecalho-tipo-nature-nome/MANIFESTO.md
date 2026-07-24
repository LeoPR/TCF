# MANIFESTO — Ciclo A: cabeçalho single-col (tipo × nature × nome)

**Declarado ANTES de medir** (protocolo do [plano `.8`](../../../notas/2026-06/tcf8-estrutura-plano.md)
§3.1 e §8.2). Versão do protocolo: `cicloA-v1`. Alterar a matriz depois de ver resultado = nova versão
declarada explicitamente, nunca edição silenciosa.

## Pergunta focal (§S1)

**Qual é a menor moldura canônica que declara apenas o que o body não permite deduzir — e como TIPO,
NATURE/spec e NOME de coluna coexistem sem ambiguidade?**

## Escopo — o que NÃO varia

- **BODY CONGELADO** no vigente em todas as células. Só a **moldura** varia. (Evita fazer moldura e
  representação ao mesmo tempo.)
- **`order_free` FORA** — [adiado pro `.9`](../../../notas/2026-07/2026-07-23-2324-order-free-e-ordenacao-adiado-09.md).
- Sem weld. Nada em `src/tcf/`.

## Eixo 1 — gramática candidata (4)

| id | forma | hipótese |
|---|---|---|
| **G1** | `#TCF.8 {nome}:{id}` — slot ÚNICO: tipo e nature dividem o namespace `{id}` | deve **falhar** por colisão tipo↔nature |
| **G2** | `#TCF.8:{tipo} {nome}:{nature}` — tipo no discriminador, nature no sufixo (**eixos separados**) | candidato forte (§S1.6 namespaces distinguíveis) |
| **G3** | `#TCF.8{tipo} {nome}:{nature}` — tag colada no índice 6 | deve **falhar**: índice 6 é o Eixo-1 (estrutura: `M`/`H`/espaço/`\n`) |
| **G4** | `:{tipo} {nome}:{nature}` — sem assinatura | contraprova: mede bytes, mas **não identificável externamente** |

## Eixo 2 — combinação de campos (a pergunta do owner)

`tipo` ∈ {ausente, `b`, `n`} × `nature` ∈ {ausente, `cpf`} × `nome` ∈ {ausente, simples, adversarial}

**Nomes adversariais** (onde os campos brigam): contendo `:` · espaço · `\` · `\n` · nome = `M` ·
nome = `H` · nome = `b` (**igual a uma tag de tipo**) · nome = `cpf` (**igual a um id de nature**) ·
nome vazio.

## Eixo 3 — conteúdo (mínimo inspecionável, body vigente)

`N=0` · `N=1` · string órfã · bool pequeno · nature single (CPF placeholder seguro).

## Contraprovas obrigatórias (devem FALHAR ALTO)

`#TCF.8` · `#TCF.8 ` · `#TCF.8:` · tag vazia · tag desconhecida · duas grafias equivalentes (só a
canônica aceita) · header sem `\n` · nome com escape solto no fim.

## Critérios avaliados (§S1, os mecanicamente testáveis)

1. **autocontenção** — parse só do wire
2. **canonicidade** — 1 dataset + 1 config → 1 grafia (grafia alternativa rejeitada)
3. **dispatch local** — rota decidida sem varrer o body
4. **prefixo sem ambiguidade** — nenhuma forma é prefixo perigoso de outra nem colide com
   `#TCF.8M` / `#TCF.8H` / `#TCF.8 ` / `#TCF.8\n` / órfão
5. **fail-loud** — malformado rejeitado com erro acionável
6. **extensibilidade** — tipo, nature e nome em namespaces distinguíveis
8. **custo total** — bytes de header

*(§S1.7 inspeção, §S1.9 streaming e §S1.10 paridade S/M/H são de julgamento — vão como leitura, não
como célula automática.)*

## Classificação de cada campo

Para cada candidato, cada campo é marcado **deduzido** / **default-da-versão** / **escrito**.

## Critério de sucesso do ciclo

O ciclo **não** escolhe gramática. Entrega a tabela propriedades × wire real, com as colisões
materializadas em arquivo. Uma gramática só avança se fechar TODAS as contraprovas.

---

## `cicloA-v2` — emenda declarada (2026-07-23, APÓS a rodada v1)

A v1 rodou e expôs **uma falha na própria matriz** (não nos candidatos). Declarada aqui em vez de
editada em silêncio, conforme a regra do topo.

**O que a v1 errou:**

1. **Direção errada do teste de colisão.** A v1 checava "o header que gerei *parece* uma forma
   existente?". O perigo real é o **inverso**: "o **parser** do candidato **engole** uma forma
   existente?". A v1 marcou G3 com **0 colisões** enquanto o `01-malformed-results.json` mostrava que
   `g3_parse("#TCF.8M")` devolve `tipo="M"` e `g3_parse("#TCF.8H")` devolve `tipo="H"` — G3 sequestra
   as rotas multi-col e hierárquica. O `result.md` da v1 ficou auto-contraditório ("refutada: 0 colisões").
2. **Falso positivo em G1.** As 33 "colisões" de G1 eram o header começar com `#TCF.8 ` — mas G1 **é**
   legitimamente a forma-espaço vigente estendida. Extensão ≠ colisão.
3. **Faltavam tags de tipo adversariais.** `TIPOS` era `{None, b, n}`; nunca exercitou uma tag `M` ou
   `H`, que é justamente o que materializa a hipótese "índice 6 é do Eixo-1".

**Correções da v2:**

- `TIPOS` += `M`, `H` (tags adversariais que colidem com o Eixo-1).
- Métrica de colisão substituída por **duas, com direção explícita**:
  - **`hijack`** (por gramática) — o parser aceita uma forma EXISTENTE como header tipado válido.
    É o teste decisivo do slot do discriminador.
  - **`rota_confundida`** (por célula) — o header gerado começa com o prefixo de uma rota existente
    **diferente** daquela que a gramática legitimamente estende (campo `EXTENDE`).
- `EXTENDE` declarado: G1→`#TCF.8 ` · G2→(nenhuma, abre `#TCF.8:`) · G3→(nenhuma) · G4→(nenhuma).

**Não muda**: body congelado, `order_free` fora, eixos de nome/nature/conteúdo, contraprovas.

---

## `cicloA-v3` — REESCRITA (2026-07-23, correção do owner)

**As v1/v2 eram inválidas como lab.** Eram manipulação ABSTRATA de strings: sem dataset, sem JSON,
sem `encode`/`decode`, sem roundtrip, sem `inputs/`+`intermediates/`+`outputs/` reais. Violavam a
convenção do catálogo [`2026-07-23-0204`](../2026-07-23-0204-api-8-catalogo-de-casos/) e o fluxo
§3.2 do plano. Pior: **inventaram comportamento** em vez de medir o real.

**O que as v1/v2 inventaram (e a v3 corrige com evidência):**

| v1/v2 inventou | realidade medida (v3) |
|---|---|
| um escaping `esc()`/`unesc()` de nome | o formato **PROÍBE** `:`/`\n` no nome (fail-loud) — A6/A6b |
| forma (1) "refutada" por colisão tipo↔nature | forma (1) **funciona hoje** e é **robusta** a nome `b`/`M` — A3/A4/A5 |
| forma (3) tratada como candidata | **não existe**: `name=` sem `nature=` é rejeitado — A6c |
| gramáticas G1–G4 de invenção própria | as **6 formas enumeradas pelo owner**, ancoradas nos wires reais |

**Regras da v3 (herdadas do catálogo e do §3.2):**

1. Fluxo materializado por caso: `inputs/<ID>-fonte.json` → `intermediates/<ID>-dataset-consumido.json`
   → `outputs/<ID>-wire.tcf` → `outputs/<ID>-dataset.roundtrip.json`.
2. **`outputs/` só contém o que o TCF REALMENTE emite.** Gramáticas hipotéticas vivem em
   `intermediates/`, marcadas como hipótese — nunca como se fossem saída.
3. Contraprovas (fail-loud) são caso de primeira classe: sem wire, com o erro real registrado.
4. Nenhuma conclusão sem wire real por trás.
