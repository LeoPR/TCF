# Ciclo A (v3) — cabeçalho single-col: fluxo REAL de dados

Fluxo §3.2 do plano: `inputs/-fonte.json` -> `intermediates/-dataset-consumido.json` -> `outputs/-wire.tcf` (REAL) -> `outputs/-dataset.roundtrip.json`. As gramáticas hipotéticas ficam em `intermediates/`, NUNCA em outputs.

- **A1** — string órfã — sem header nenhum (piso: o TCF não escreve moldura)
    - investiga: o que o formato faz quando NADA precisa ser declarado
    - fonte: `['ana@site.com', 'ana.b@site.com', 'carlos@site.com']`
    - wire REAL (27 B), linha-0: `(órfão)`
    - roundtrip: ✅
- **A2** — nature CPF SEM nome — forma (1) com nome vazio == forma (5)
    - investiga: forma (5) `#TCF.8:{id}` é o caso degenerado de (1) com nome vazio?
    - fonte: `['111.111.111-11', '222.222.222-22', '333.333.333-33', '111.111.111-11`
    - wire REAL (35 B), linha-0: `#TCF.8 :cpf`
    - roundtrip: ✅
- **A3** — nature CPF COM nome 'doc' — forma (1) completa, REAL hoje
    - investiga: forma (1) `#TCF.8 {nome}:{id}` — já existe em produção
    - fonte: `['111.111.111-11', '222.222.222-22', '333.333.333-33', '111.111.111-11`
    - wire REAL (38 B), linha-0: `#TCF.8 doc:cpf`
    - roundtrip: ✅
- **A4** — nature CPF com nome 'b' (= colide com uma TAG DE TIPO hipotética)
    - investiga: nome igual a tag de tipo quebra a forma (1)?
    - fonte: `['111.111.111-11', '222.222.222-22', '333.333.333-33', '111.111.111-11`
    - wire REAL (36 B), linha-0: `#TCF.8 b:cpf`
    - roundtrip: ✅
- **A5** — nature CPF com nome 'M' (= colide com o Eixo-1 multi-col)
    - investiga: nome igual a discriminador de ESTRUTURA quebra a forma (1)?
    - fonte: `['111.111.111-11', '222.222.222-22', '333.333.333-33', '111.111.111-11`
    - wire REAL (36 B), linha-0: `#TCF.8 M:cpf`
    - roundtrip: ✅
- **A6** — nature CPF com nome contendo ':' — contrato REJEITA (não escapa)
    - investiga: o formato ESCAPA ou PROÍBE o separador no nome?
    - resultado: `FAIL-LOUD (esperado): ValueError: name de single-col nao pode conter ':' nem '\n' (reservado pro meta #TCF.8): 'a:b'`
- **A6b** — nature CPF com nome contendo LF — idem
    - investiga: idem A6 para quebra de linha
    - resultado: `FAIL-LOUD (esperado): ValueError: name de single-col nao pode conter ':' nem '\n' (reservado pro meta #TCF.8): 'a\nb'`
- **A6c** — name= SEM nature — rótulo sozinho não existe (forma (3) não é suportada)
    - investiga: a forma (3) `#TCF.8 {nome}` existe hoje?
    - resultado: `FAIL-LOUD (esperado): ValueError: name= so' tem efeito em single-col COM nature= (rotulo do header '#TCF.8 nome:spec'); sem isso seria ignorado calado`
- **A7** — lista de BOOL — hoje NÃO tem forma single-col tipada (vai pro .8H)
    - investiga: A LACUNA que motiva o estudo: tipo não tem onde morar em single-col
    - fonte: `[True, False, True, True]`
    - wire REAL (41 B), linha-0: `#TCF.8H#V\z#:3[]:17b`
    - roundtrip: ✅
- **A8** — lista de INT — mesma lacuna
    - investiga: idem A7 para number
    - fonte: `[1, 2, 3]`
    - wire REAL (31 B), linha-0: `#TCF.8H#V\z#:3[]:8n`
    - roundtrip: ✅
- **A9** — version-stamp — ocupa o índice 6 com '\n'
    - investiga: prova que o índice 6 é o eixo de ESTRUTURA, não de tipo
    - fonte: `['a', 'ab', 'abc']`
    - wire REAL (16 B), linha-0: `#TCF.8`
    - roundtrip: ✅

## Análise das 6 formas

Íntegra em [`intermediates/00-analise-6-formas.txt`](intermediates/00-analise-6-formas.txt). Resumo:

| forma | status | índice 6 | evidência | veredito |
|---|---|---|---|---|
| (1) `#TCF.8 {nome}:{id}` | **REAL hoje** | `' '` | A2/A3/A4/A5 | **robusta** — nome `b` e `M` funcionam |
| (2) `#TCF.8{nome}:{id}` | hipotética | 1º char do NOME | — | frágil (contraste c/ A5) |
| (3) `#TCF.8 {nome}` | **não existe** | `' '` | A6c rejeita | rótulo sozinho não é rota |
| (4) `#TCF.8{nome}` | hipotética | 1º char do NOME | — | **indistinguível de (6)** + frágil |
| (5) `#TCF.8:{id}` | hipotética *sem espaço* | `':'` (livre) | A2 é a versão COM espaço | `:` livre no Eixo-1 → discriminador novo viável |
| (6) `#TCF.8{id}` | hipotética | 1º char do ID | — | **defensável** — id é namespace FECHADO |

### A diferença entre (4) e (6) — o cerne

Como **forma** são idênticas (`#TCF.8` + token nu). O que as separa é a **natureza do token**: **nome** é ABERTO (dado do usuário — não dá pra restringir sem quebrar contrato) e **id** é FECHADO (vocabulário do formato — dá pra excluir `M`/`H` por definição). Por isso (6) é defensável e (4) não. A sua intuição de que 4 e 6 se confundem **se confirma**.

### Por que a forma (1) NÃO quebra com nome colidente (evidência)

- A4 → `#TCF.8 b:cpf` (nome `b`, igual a uma tag de tipo) — **funciona**
- A5 → `#TCF.8 M:cpf` (nome `M`, igual ao discriminador multi-col) — **funciona**

Porque o índice 6 é o **espaço** (a marca da rota), então o 1º char do nome nunca compete com o Eixo-1; e o id é separado pelo **último** `:`.

### Escaping: o formato PROÍBE, não escapa

A6 (`name='a:b'`) e A6b (`name='a\nb'`) são **rejeitados**: *"name de single-col nao pode conter ':' nem '\n'"*. O separador é protegido por **contrato fail-loud**, não por sequência de escape — simplifica o parse ao custo de restringir nomes.

### Combinação que a evidência favorece: **(1)+(6)**

O espaço marca 'tem nome' (rota 1, já real e robusta); a ausência marca 'token nu do namespace fechado' (rota 6). Sem ambiguidade. A sua hipótese de que ` ` e `:` desambiguam é **parcialmente** verdadeira: eles separam as rotas, mas (2)/(4) continuam expondo o índice 6 a nome arbitrário — o conjunto (1)+(2)+(5)+(6) só fecha se (2) proibir nome iniciando em char reservado, reintroduzindo no NOME a restrição que (1) evita de graça.

### ⚠️ Correção da v2 deste lab

A v2 declarou a forma (1) **'refutada'** — **estava errado**. Ela funciona hoje (A3) e é robusta a nome colidente (A4/A5). Aquela 'refutação' vinha de um enquadramento que eu inventei (tipo e nature disputando o mesmo slot), não do comportamento real. As v1/v2 também inventaram um escaping `esc()`/`unesc()` que **não existe** — o formato proíbe.

---
**Roundtrip: 8 OK, 0 falhas.** Artefatos: `inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `intermediates/*.debug.txt` · `intermediates/00-analise-6-formas.txt` · `outputs/*-wire.tcf` · `outputs/*-dataset.roundtrip.json`. Regenera: `python run.py`.
