# ADR-0045 — Bordas em valor de spec: fechar o vazamento, nomear a variante, não uniformizar o LF

- **Status**: **aceito — SOLDADO** (2026-08-21, aprovação do owner). Suíte **1307**; gates
  byte-canônicos intactos (D17a=300, D1–D9, real-world); snippets 71/0.
- **Escopo**: `_CPF_RE`, `_CNPJ_RE`, `_IPV4_RE` (o `$`), e `classify_value` dos dois specs
  templated (o rótulo novo). **Não** toca encoder, decoder nem gramática do wire.
- **Interage com**: ADR-0015 (natures) · `output-convention.md` §3 (corrigida no mesmo dia) ·
  `BUG-CHAVE-VAZIA-POSICIONAL` (mesma classe: o formato altera o dado)
- **Origem**: revisão adversarial do ADR-0044 achou o vazamento; o owner reenquadrou como
  "trim de bordas" e pediu tratamento separado por eixo.

---

## Contexto

A revisão do ADR-0044 achou que `'11.222.333/0001-81\n'` classificava como `compressible` e o
round-trip **perdia o `\n`**. Registrei como "bug do `$`" e o owner reenquadrou:

> *"nesse caso é similar a se comportar como um trim de bordas, quando tem espaços por exemplo
> [...] o spec se interessa pelo tipo do dado, e restos poderiam ser ignorados (por flag) [...]
> uma é deixar ele mais preguiçoso, e dar um warning e tolerar e fazer trim, por outro lado,
> poderia ser mais rígido [...] tem que ver se isso não é falha do construtor [...] o comum é o
> dado entrar OK [...] tratar apenas o comum, e o incomum a gente tolera perda de performance e
> emissões de warning."*

O reenquadramento mudou o diagnóstico. Testando as **dez** formas de borda (lab `0330`):

| borda | comportamento |
|---|---|
| espaço (esq/dir/ambos), tab, CR, CRLF, LF duplo, LF à esquerda | literal, **RT ok** |
| **LF único à direita** | comprime, **perde o caractere** |

**O TCF não faz trim.** Nove de dez bordas já caem em literal corretamente. O que existia era um
**trim invisível, mudo, de exatamente um caractere**, causado pela semântica do `$` em Python
(casa no fim da string **ou** antes de um `\n` final). Não era política — era vazamento.

Prevalência medida: **zero** em 20 000 linhas reais. Mas as fontes plausíveis são de
**ingestão**, e a mais comum de todas — `for line in f:` sem `.strip()` — produz exatamente a
borda que vazava.

## Decisão 1 — Fechar o vazamento: `$` → `\Z`

Em `_CPF_RE`, `_CNPJ_RE` e `_IPV4_RE`. O `data-iso` **não precisa**: o `classify_value` dele
já **checa o comprimento** (`len(v) != 10`) antes da regex — a defesa que os outros não tinham.

**Custo medido: zero.** `\Z` e `$` são idênticos quando não há LF final: **0 divergência de
byte em 9 012 valores** sem borda. Resolve 6/6 dos casos que perdiam dado.

Isso **não escolhe postura nenhuma** — apenas torna o comportamento uniforme: toda borda cai em
literal, o RT sempre se preserva.

## Decisão 2 — Nomear a variante: `format_bordered`

Um valor com borda **continua não sendo comprimido**. As três posturas foram medidas (por
valor, lab `0330`):

| postura | bytes | RT |
|---|---:|---|
| **rígido** (literal) — o que 9/10 já faziam | 20 B | ok |
| preguiçoso (trim + comprime) | 7 B | **perde a borda** |
| lazy (comprime + restaura a borda) | 10 B | ok, mas **gramática nova** |

O preguiçoso é 13 B mais barato — e é **exatamente o bug que estamos consertando**. Adotá-lo
como política seria escolher quebrar o round-trip byte-canônico, que é constituição do formato
(mesma classe do `BUG-CHAVE-VAZIA-POSICIONAL`). **Rejeitado.**

Mas o owner tem razão de que o incomum merece sinal. O canal **já existe**
(`SideOutputs.nature_apply.by_status`); faltava o **rótulo**. `format_mismatch` diz *"não
reconheço essa forma"*; `format_bordered` diz outra coisa, e é **acionável**: *o dado está
certo, o pipeline a montante é que está sujo*.

**Bytes idênticos** — continua literal. Muda só a telemetria. E segue a taxonomia existente:
`format_unmasked` e `format_padded_zeros` já são exatamente isto — rótulos de variante
reconhecível que não comprime.

O rótulo é **estreito de propósito**: só é `format_bordered` o que vira `compressible` depois
do trim. Lixo com borda continua `format_mismatch`; DV errado continua `check_invalid`.

**Custo no caminho comum: nenhum.** 50 000 `classify_value` em valores limpos, com e sem a
guarda `v != v.strip()`: **−4,2%**, dentro do ruído. O `classify_value` já varre caractere a
caractere. A tensão "comum × incomum" que o owner antecipou **não existe aqui**.

## Decisão 3 — NÃO uniformizar a emissão do LF final entre rotas

O lab `0400` mostrou que **7 rotas emitem** o LF final e **3 não** (multi-col, multi-col n=1,
tipado bool). Uniformizar parecia higiene. **Medido, não é:**

| rota | acrescentar o LF faria |
|---|---|
| multi-col | o decoder **rejeita** (`ValueError`) |
| multi-col n=1 | **muda a semântica** — a coluna ganha um valor vazio |
| tipado bool | o decoder **rejeita** (`ValueError`) |
| gate D17a | **300 → 301 B** — quebra o gate byte-canônico |

Ou seja: exigiria mudar **encoder e decoder** em duas rotas, mudar semântica numa terceira, e
re-pinar baseline — para ganhar consistência estética e **perder 1 byte por wire**. **Não
fazer**, e a razão fica registrada para não ser reaberta como "higiene óbvia".

Fica em **H-15-08** como assimetria **conhecida e precificada**, não como pendência vaga.

## Consequências

- **Nenhum byte de wire muda.** O `\Z` só altera valores com LF final (que passam a ser
  literal em vez de comprimido-com-perda), e o `format_bordered` é rótulo. Gates intactos.
- **Uma classe de corrupção silenciosa deixa de existir** nos três specs atingidos.
- **A telemetria fica acionável** para a causa mais comum de sujeira de ingestão.
- **Fora de escopo, declarado**: a postura *lazy* (comprimir + restaurar a borda) ganharia
  ~10 B/valor sobre o literal e preserva o RT, mas exige gramática nova no payload → estudo
  `.9`, e só se a prevalência real justificar. Hoje ela é zero no dado armazenado.
- **Não testado**: NBSP e outros espaços Unicode. O `.strip()` os trata; a regex não. Se
  aparecerem, cairão em `format_bordered` (porque `.strip()` os remove) — o que é o rótulo
  certo, mas não foi verificado.

## Alternativas rejeitadas

- **Trim preguiçoso como default** — 13 B mais barato, mas quebra o RT byte-canônico. Se um dia
  fizer sentido, tem de ser **flag explícita do chamador** (`trim=True`), nunca default
  silencioso.
- **Deixar como estava** — o vazamento é da classe que altera o dado, e a fonte de ingestão mais
  comum o produz.
- **Uniformizar o LF entre rotas** — ver Decisão 3.

## Evidência

- [`2026-08-21-0330-bordas-em-spec`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0330-bordas-em-spec/)
  — os 4 eixos (matriz de bordas, prevalência, 3 posturas, custo da guarda)
- [`2026-08-21-0400-lf-final-do-wire`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0400-lf-final-do-wire/)
  — as 10 rotas e a prova de que o LF final é terminador
- [`0230/h15_07_raio.py`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0230-cnpj-unificado/h15_07_raio.py)
  — o raio do vazamento e o custo do conserto
