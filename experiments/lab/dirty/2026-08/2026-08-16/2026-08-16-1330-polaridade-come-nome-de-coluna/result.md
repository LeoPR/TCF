# Resultado — o defeito, o alcance e a fronteira

**RT quebrado silenciosamente** em coluna única cujo nome termina em pontuação, no `.8M` **e**
no `.8H`. Reproduzido, mecanismo identificado, causa isolada por contra-prova.

## 1. O alcance

| rota | RT falso | modo de falha |
|---|---:|---|
| `.8M` (1 coluna, n≥5) | **48/64 = 75,0%** | 24 perdem a chave · 24 perdem chave **e** valores |
| `.8H` (1 campo) | **38/64 = 59,4%** | mesmo mecanismo |
| **warnings** | **0/64** | perda inteiramente silenciosa |

Os 16 que escapam terminam em `* , : = \ ^ | ~`.

## 2. A causa, isolada

A contra-prova é limpa: **a mesma coluna com uma segunda ao lado dá 64/64 RT ok**. Com 2+
colunas o meta ganha `,`/`=`, o nome deixa de ser o fim da linha 1, e a polaridade não o
alcança. **O defeito é da coluna única.**

## 3. A dependência de `n`, que é o motivo de não ter sido pego

O gatilho não é o nome — é o **modo** que vence o `min()`, porque o modo põe ou não um prefixo
antes do nome:

```
n=3   #TCF.8M!obs.   modo raw, prefixo '!'    RT ok
n=5   #TCF.8Mobs.    modo tcf, prefixo vazio  RT QUEBRA
```

Qualquer teste de round-trip escrito com uma coluna pequena passa. É a mesma classe do
`T-GRAFIA-CHECKLIST` (*"a frase no ADR não impediu — o teste é que impede"*), mas desta vez a
assimetria não está dentro de uma camada: está **entre duas** — a polaridade é camada de borda
(`decoder.py:150-153`: *"a PRIMEIRA coisa do decode"*) e por construção não conhece a gramática
do `.8M`.

## 4. Severidade

É a pior classe do projeto: **resposta errada sem erro**. Pior que o `T-NATURE-IGNORADA-CALADA`
(lá o wire sai certo e só a expectativa quebra) e pior que o `T-VIEW-PRED-POSICIONAL` (lá a
consulta erra mas o dado está íntegro). **Aqui o dado sai do round-trip diferente do que
entrou**, e em 24 dos 64 casos os valores — não só a chave.

Nomes plausíveis em dado real que caem: `obs.`, `qtd.`, `valor_r$`, `%`, `medida(m)`, `nome-`,
`id#`. Nomes com `.` final são comuns em export de planilha.

## 5. O que este lab NÃO fez

- **Não consertou.** `src/tcf` intocado; conserto exige aprovação e decisão de onde cortar
  (escapar o nome contra o alfabeto da polaridade no emissor, ou ensinar a polaridade a não
  agir quando o disc é `M`/`H` — são fronteiras diferentes com custos diferentes).
- **Não varreu Unicode** — só `string.punctuation` ASCII.
- **Não mediu multi-coluna com a ÚLTIMA coluna terminando em pontuação sob `drop_names`**, que
  é a outra forma em que o nome pode encostar no fim da linha 1.

---

## 6. CONSERTADO — 2026-08-16, opção B (aprovada pelo owner)

**O fix**: escopo de discriminador em `decoder.py` — o pré-passe de polaridade só age quando o
disc **não** é `M`/`H`.

**A premissa, medida antes de mexer**: o encode nunca polariza essas rotas. Está declarado em
`encoder.py:489` (*"`.8M`/`.8H`/spec ficam de fora deste weld"*), os três sítios de
`polariza()` são single-col, e o Bloco 6 mediu **2.000 wires `.8M` + 2.000 `.8H`, zero com
sufixo separável**. Rodar o pré-passe ali só podia errar.

### O antes/depois, do mesmo `run.py`

| métrica | antes | depois |
|---|---:|---:|
| `.8M` RT falso (de 64) | **48** | **0** |
| `.8H` RT falso (de 64) | **38** | **0** |
| variações novas quebradas (de 19) | 3 | **0** |
| contra-prova 2 colunas ok (de 64) | 64 | 64 |
| warnings | 0 | 0 |

**O wire não mudou**: os headers das 19 variações e dos 5 controles single-col são
**byte-idênticos** entre as duas rodadas (0 diferenças), e os gates byte-canonical seguem
verdes. Custo em bytes do conserto: **zero**.

### O que as variações novas acrescentaram (Bloco 4)

- **Unicode é SEGURO** — `obs°`, `valor€`, `medida±`, `temp℃`, `ção…` sempre fecharam, porque
  a `FAIXA` da polaridade é ASCII 0x21–0x7E. **Resolve o viés que a versão anterior deste lab
  declarava** (*"só ASCII"*).
- **Três casos novos do MESMO defeito** que o sweep `ab`+pontuação não alcançava: nome `.`,
  nome `..` e nome `a.` (o sweep começava com dois chars alfanuméricos).
- **`min_header=False`, 3 colunas, spec `:dt`, `.8H` aninhado e os modos `!`/`@`/`%` já eram
  seguros** — em todos o meta ganha `=`/`,`/`:`/prefixo, e o `tag.isalnum()` do separador
  falha, que é a conservadoria que já existia.
- **`drop_names` era erro do meu teste, não defeito**: com ele os nomes viram posicionais por
  design (ADR-0029), então a prova é por VALORES. Corrigido no `run.py`.

### O pino na suíte

`TestPolaridadeComeNome` em `tests/test_f0_boundary_fixes.py` — 16 casos. Verificado por
`git stash` do fix: **13 dos 16 falham sem ele**, os 16 passam com ele. Os 3 que passam nos
dois são as contra-provas (single-col polarizado não regride; o encode nunca polariza `M`/`H`).
Suíte **1269 → 1285 passed**.
