# 2026-08-21-0330 — bordas em valor de spec: a reavaliação em 4 eixos

> ## ⚑ SOLDADO 2026-08-21 — [ADR-0045](../../../../../../docs/adr/0045-bordas-em-valor-de-spec.md)
>
> O owner aprovou as três peças. Foram para `src/tcf`: **(1)** o vazamento fechado (`$`→`\Z`
> nas 3 regex, 0 divergência de byte em 9 012 valores); **(2)** o status `format_bordered`
> (bytes idênticos, telemetria acionável) — nos **dois** tipos de spec, templated-checked e
> templated-padded. **(3)** A postura *lazy* NÃO foi soldada: segue como estudo `.9`.
>
> Suíte 1304 → **1307**; gates byte-canônicos intactos.

Reavaliação do **H-15-07** a pedido do owner, que reenquadrou o problema:

> *"nesse caso é similar a se comportar como um trim de bordas, quando tem espaços por exemplo
> [...] o spec se interessa pelo tipo do dado, e restos poderiam ser ignorados (por flag) [...]
> uma é deixar ele mais preguiçoso, e dar um warning e tolerar e fazer trim, por outro lado,
> poderia ser mais rígido e exigir que seja limpo [...] tem que ver se isso não é falha do
> construtor [...] o comum é o dado entrar OK [...] tratar apenas o comum, e o incomum a gente
> tolera perda de performance e emissões de warning."*

**Quando este lab foi escrito, nada estava soldado** — era reavaliação para decisão. As três
peças foram aprovadas no mesmo dia; o banner acima diz o que virou código e o que não.

---

## E1 — "É erro do teste?" Em parte. Mas o achado é outro.

**Sim, eu construí o `\n`.** Nenhum dado nasceu assim no lab. Mas ao testar as **dez** formas
de borda apareceu algo que não é sobre o meu teste:

| borda | status | RT |
|---|---|---|
| nada | `compressible` | ok |
| espaço à esquerda / direita / nos dois | `format_mismatch` | ok |
| tab à direita | `format_mismatch` | ok |
| **LF à direita** ⟵ *o defeito* | **`compressible`** | **PERDE** |
| CR à direita | `format_mismatch` | ok |
| CRLF à direita | `format_mismatch` | ok |
| LF duplo | `format_mismatch` | ok |
| LF à esquerda | `format_mismatch` | ok |

> A tabela acima é o estado **PRÉ-weld**. Depois do ADR-0045 a linha do LF virou
> `format_bordered` com RT ok, como as outras nove.

**O TCF não faz trim nenhum** — 9 das 10 bordas caem em literal com o roundtrip intacto. A
única exceção era um **vazamento acidental** do `$` da regex, que em Python casa também antes
de *um* LF final.

Então a pergunta certa não é "devemos fazer trim?". É: **hoje existe um trim invisível, mudo,
de exatamente um caractere, que ninguém escolheu.** Qualquer que seja a política adotada, essa
inconsistência é defeito — porque o comportamento não é o que nenhuma das três posturas
descreve.

**E o `data-iso` escapa — e mostra a defesa certa.** Ele não é atingido porque seu
`classify_value` **checa o comprimento explicitamente** (`len(v) != 10` → `length_wrong`)
antes de chegar à regex. CPF, CNPJ e IP não têm essa checagem. A lição vale mais que o
remendo: **validar comprimento é a barreira, e ela já existe num dos quatro specs**.

## E2 — Possibilidade de ocorrer: rara no armazenado, plausível no recebido

**Dado real (Shaper, `receita-cnpj-enderecos`, 20 000 linhas, 11 campos texto): zero valores
com borda.** A fonte entrega limpo — o owner está certo de que o comum é o dado entrar OK.

Mas prevalência-no-dataset não é prevalência-no-mundo: esse dataset já passou por limpeza. As
fontes reais de borda são de **ingestão**, não de banco:

- `for line in f:` sem `.strip()` — **o LF do arquivo vem dentro do valor**, e é exatamente o
  caso que vaza hoje;
- coluna `CHAR(18)` de banco — padding com espaço à direita;
- copy/paste de planilha ou PDF — espaço e NBSP nas pontas;
- CSV com espaço depois da vírgula sem `skipinitialspace`.

Ou seja: **improvável no dado armazenado, plausível no dado recebido** — e a fonte mais
plausível de todas produz justamente a única borda que hoje corrompe.

## E3 — O que fazer se ocorre: as 3 posturas, medidas

| caso | **rígido** (hoje, 9/10) | **preguiçoso** (trim) | **lazy** (restaura) |
|---|---:|---:|---:|
| LF à direita | 20 B | 7 B | 10 B |
| espaço nos dois | 23 B | 7 B | 13 B |
| tab à direita | 20 B | 7 B | 10 B |

- **Rígido** — cai em literal. RT correto. É o que 9 das 10 bordas já fazem.
- **Preguiçoso** — 7 B, mas **perde a borda**. Aqui está o ponto: **é exatamente o
  comportamento de hoje para o LF** — só que hoje ele é acidental, mudo, e só para um
  caractere. Adotá-lo como política seria escolher conscientemente quebrar o roundtrip
  byte-canônico, que é constituição do formato.
- **Lazy com restauração** — comprime o miolo e grava a borda como afixo restaurável. RT
  correto e **~10 B melhor que o literal por valor**. Mas exige **gramática nova** no payload
  (contagem + chars da borda), o que é mudança de formato → `.9`, não `.8`.

## E4 — O comum × o incomum: a guarda é grátis

50 000 `classify_value` em valores **limpos**, melhor de 3:

```
sem guarda : 699,8 ms
com guarda : 670,5 ms   (−4,2%, ou seja indistinguível do ruído)
```

A guarda `v != v.strip()` **não aparece** — o `classify_value` já varre caractere a caractere,
e um `strip` a mais some no ruído. O princípio do owner ("tratar o comum, tolerar o incomum")
se aplica sem tensão aqui: **não há custo a tolerar no caminho comum**.

## O warning: o canal já existe, falta o rótulo

```
by_status: {"compressible": 1, "format_mismatch": 2, "check_invalid": 1}
```

Os valores bordados **já aparecem** na telemetria (`SideOutputs.nature_apply.by_status`) — mas
como `format_mismatch`, misturados com "não reconheço essa forma". Um rótulo próprio diria
**"isto É um CNPJ, com lixo de borda"** — acionável para limpar o pipeline a montante.

E há precedente na própria taxonomia: `format_unmasked` e `format_padded_zeros` existem
exatamente para nomear **variante reconhecível que não comprime**.

---

## Recomendação — três peças separáveis, em ordem de custo

*(Foi o que eu propus; as três foram aprovadas. 1 e 2 viraram código, 3 continua estudo `.9` —
ver o banner no topo.)*

**1. Fechar o vazamento (`$` → `\Z`).** Não escolhe postura nenhuma; só torna o comportamento
**uniforme**: toda borda → literal, RT sempre correto. Medido: resolve 6/6 dos casos que
perdiam e custa **0 divergência de byte** em 9 012 valores sem borda. Toca 3 specs
(`_CPF_RE`, `_CNPJ_RE`, `_IPV4_RE`). **✔ soldado.**

**2. Rótulo de status próprio para borda** (ex.: `format_bordered`). Bytes idênticos — continua
literal —, muda só a telemetria, que passa a ser acionável. Segue a taxonomia existente. É o
"warning" que você descreveu, no canal que já existe. **✔ soldado**, nos dois tipos de spec.

**3. Postura lazy (comprimir + restaurar a borda).** Ganha ~10 B/valor sobre o literal e
preserva o RT, mas é **gramática nova** → estudo `.9`. Só vale a pena se a prevalência real
justificar; hoje ela é zero no armazenado. **✘ não soldado** — segue estudo.

**O que eu não recomendaria**: adotar o trim preguiçoso como política. Ele é 13 B mais barato
que o literal, mas o preço é o roundtrip byte-canônico — e o projeto já tratou essa classe
como inaceitável (`BUG-CHAVE-VAZIA-POSICIONAL`, "o único caso em que o TCF altera o dado").
Se um dia fizer sentido, deveria ser **flag explícita do chamador** (`trim=True`), nunca
default silencioso.

## Não medido (declarado)

- Prevalência em dado **recebido** (não armazenado) — não temos corpus de ingestão suja.
- O custo real da postura lazy no wire completo (só modelei o payload por valor).
- NBSP e outros espaços Unicode: não testados; `.strip()` os trata, a regex não.
- Se o `format_bordered` mudaria alguma decisão do FLOOR (não deve — literal é literal).

## Evidência

[`run.py`](run.py) com os 4 eixos e asserts (a matriz de bordas afirma que **exatamente uma**
variante perde). [`resultado.json`](resultado.json) · 3 arquivos em `inputs/`+`outputs/` com
roundtrip e portão anti-órfão.

## Conexões

- **H-15-07** no [registry de hipóteses](../../../notas/2026-05/roadmap-hipoteses.md)
- Raio medido do vazamento: [`0230/h15_07_raio.py`](../2026-08-21-0230-cnpj-unificado/h15_07_raio.py)
- Classe do `BUG-CHAVE-VAZIA-POSICIONAL` (o formato altera o dado) — ver `STATUS.md`
