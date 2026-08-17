# Estado do formato — tipos, rotas e modos (síntese de 2026-08)

> **Owner (2026-08-16)**: *"faça um readme atualizado acima dos labs dando a conclusão geral
> de cada um dos tipos e as etapas single, multi, modos, etc."*

Este README fica **acima dos labs** de propósito: os labs respondem perguntas, este documento
diz **onde cada coisa parou**. Todo número aqui tem lab ou ticket atrás — se não tiver, está
marcado como não-medido.

Fonte viva: [`STATUS.md`](../../../../STATUS.md). Índice do dia mais recente:
[`2026-08-16/INDEX.md`](2026-08-16/INDEX.md).

---

## 1. As três rotas — o que cada uma alcança

| | quando entra | candidatos que consulta | estado |
|---|---|---|---|
| **single-col** (flat e tipado) | `list` de escalares | core · **polaridade** · **bN de domínio** · **denso b1/b2** (bool) · nature/spec | a mais completa |
| **multi `.8M`** | `dict[str, list[str]]` retangular, **tudo string** | core · **raw `!`** · **dict `@`** · **split `%`** · nature no FLOOR | **auditada em corpus, saudável** |
| **hier `.8H`** | tudo o mais (tipado, ragged, aninhado, vazio) | **UM candidato só** | o buraco grande |

**A assimetria é o fato central do formato hoje.** Os conjuntos de candidatos são
**quase disjuntos**: o single tem bN e polaridade que o multi não tem; o multi tem raw, dict e
split que o single não tem. É o `T-UM-CAMINHO-SO`.

### O `.8M` — auditado em 23 tabelas / 186 colunas (lab [`2130`](2026-08-16/2026-08-16-2130-auditoria-do-M-no-corpus/))

RT **23/23** · paridade `view`×`decode` **23/23** · as 6 invariantes de fronteira **23/23**,
incluindo **decode paralelo == serial** · guards com **zero disparo espúrio** · os 4 candidatos
**todos com domínio real** (dict 70 · tcf 59 · split 37 · raw 20 colunas).

O que ele deixa na mesa por não ter bN/polaridade: **2,3% do corpus** (77 de 186 colunas
teriam candidato melhor no flat). A razão **por coluna** chega a **5,82×**, mas só 10 colunas
passam de 2× e elas são pequenas em bytes.

> ⚠️ **Correção registrada**: eu havia extrapolado do adult-census que a soma dos flats batia
> o `.8M` em +27,2%. No corpus inteiro **o `.8M` vence por 5,1%**, e o adult-census é
> justamente onde ele mais perde. O número certo é 2,3%, não 27%.

### O `.8H` — o buraco não auditado

**99,986% do overhead** dele numa tabela retangular tem **uma causa só**: `hierarchical.py:502`
comprime cada coluna com `stamp=False`, e `encoder.py:461` retorna **antes** do bloco de
candidatos. Ele não escolhe mal — **nunca chega ao `min()`**. Medido: `.8M` 41.925 B contra
`.8H` 76.949 B, com os **corpos byte-idênticos** ao `.8M(fallback=False)`.

**Nunca passou por auditoria de corpus.** É o maior item aberto em bytes.

---

## 2. Os modos — quem existe e onde vive

| modo | marcador | rota | o que faz |
|---|---|---|---|
| core (OBAT + HCC) | — | todas | tokenização por afixos, composição hierárquica |
| RLE / seq-RLE / periódico | `*N\|` `*N+d\|` `*N~…\|` | todas | runs, progressões, ciclos (ADR-0040) |
| **polaridade** | `!` no header | **single** | 1 byte por transição em vez de 1 por literal (ADR-0035) |
| **bN de domínio** | `B` / `C` | **single** | baixa cardinalidade em bits (ADR-0036) |
| **denso b1/b2** | `b`/`n` + `B` | **single tipado** | bool/int de domínio implícito (ADR-0037/0039) |
| **raw** | `!` no meta | **multi** | corpo cru quando o core não paga (ADR-0022) |
| **dict V2-B** | `@` no meta | **multi** | tabela de únicos + stream base-94 (ADR-0025) |
| **split estrutural** | `%` no meta | **multi** | template 1× + campos como sub-tabela (ADR-0026) |
| nature/spec | `:id` no header | todas | pre-tx por natureza, competindo no FLOOR (ADR-0027/0041) |

**Restrição de desenho medida** (2026-08-16): marcador de modo novo no meta do `.8M` só pode
usar char que faça `int(<char>+dígitos, 16)` **levantar** — **67 são seguros, 16 perigosos**.
Além de `a-f`/`A-F` virarem dígito hex calado, **`+`, `-`, espaço e tab** também são engolidos.
A regra antiga (*"pontuação, nunca letra"*) autorizava `+` e `-` e estava **incompleta**.

---

## 3. Os tipos — conclusão de cada um

| tipo | veredito | onde está |
|---|---|---|
| **string** | é o caso base; core + bN + dict + split cobrem | — |
| **date** | **spec SOLDADO** (`:dt`, ADR-0027). Em dado real quem vence é `componentes` (52%) e `delta` na coluna ordenada (71%); **`delta2` não venceu nenhuma vez em 24 medições** | labs [`0400`/`0530`](../2026-08-15/) |
| **bool** | **soldado** — denso b1/b2 (ADR-0037) + lazytype (ADR-0039). Domínio implícito, vence por construção | — |
| **int / número** | tipo nativo (`stype='n'`) **sem pre-transformação**. Medido **1,9×–3,0×** em progressão e largura fixa; 3 alvos nomeados (PAD, OFFPAD, B94) | `T-NUMERO-SPEC` |
| **float** | **8,0% agregado** em 12 colunas reais — **não paga um spec novo agora**. A escala vence em 8/12, o split em 4; precisão suja quebra a escala | `T-FLOAT-SPEC`, avaliado 2026-08-14 |
| **hora** | **1,03× no único dado real — não se justifica agora**. Hora quase não existe no corpus: uma coluna, e é datetime | `T-HORA-SPEC`, avaliado 2026-08-14 |
| **datetime** | **o menos avaliado e o de maior retorno estrutural**. A melhor resposta **não é um spec** — é o **split**, 7,13× num datetime real. Falta caracterizar | `T-DATETIME-TIPO` |
| **cpf / cnpj / ip** | **soldados** como natures templated | ADR-0015 |
| **`date`/`datetime`/`time`/`Decimal`/`bytes` NATIVOS** | **FAIL-LOUD na porta.** A API aceita exatamente 4 tipos: `str`→`s`, `int`/`float`→`n`, `bool`→`b` | `T-DATA-TIPADA-NATIVA`, `T-DECIMAL-HARD-RECUSADO` |

---

## 4. Compartilhamento entre colunas — o estado das três ideias

Esta seção responde direto à pergunta *"como estão o dict compartilhado, coluna
compartilhando tipo e tudo mais"*.

| ideia | o que se mediu | estado |
|---|---|---|
| **compartilhar a DECLARAÇÃO** (um marcador de modo para o grupo, em vez de um por coluna) | **teto 0,13%** do wire — o `.8M` já declara cada coluna em ~5 B com `drop_names` | **medido e pequeno demais**; não vale sozinho |
| **agrupar por TIPO comum** (o exemplo `true`/`false`) | **0,5%** com k=2. **O tipo não é a variável** — o que decide é o tamanho do domínio | **critério refutado**; o gatilho certo é domínio, não tipo |
| **dict COMPARTILHADO** (mesma tabela de únicos servindo 2+ colunas) | **k=2 → 0,5% · k=50 → 5,7% · k=500 → 21,2%**. Domínios **disjuntos rendem ZERO** | **é o `cross-dict`/`H-GDICT`**, que já mediu −19,2% em same-domain-refs e **está escopado `.9`** pelo owner (2026-06-24) |
| **cross-column genérico** (compartilhar fragmentos entre colunas quaisquer) | não medido | O-FMT-06, *"pouco explorada"*, aberta |

**A conclusão que reposiciona as três**: agrupar rende em função do **tamanho do domínio
sobreposto**, não do tipo. `origem`/`destino` com 500 cidades rende 21,2%; cinco flags
booleanas rendem 0,5%. E o gatilho é **detectável no pré-passe**, que já calcula cardinalidade
por coluna.

**O custo em paralelismo é barreira, não perda**: com domínio compartilhado o decode passa de
*N tarefas independentes* para *1 tarefa (a tabela) + N independentes*. O `view` já faz isso
dentro de uma coluna, e o H-GDICT registrou *"lazy lê o dict 1×"* como **ganho**.

**E o contexto que dimensiona tudo isso**: as três somadas valem menos que **ter o candidato
certo por coluna** (Grupo A), que por sua vez vale 2,3% do corpus. Nenhuma delas é o item
grande.

Labs: [`1610`](2026-08-16/2026-08-16-1610-agrupar-tipos-comuns-no-M/) ·
[`1450`](2026-08-16/2026-08-16-1450-ordem-de-colunas-no-M/) (a ordem já é livre — reagrupar
não custa nada hoje; falta o mecanismo, não a permissão).

---

## 5. Header e fronteira de coluna — fechados

- **O header está no piso.** O-FMT-11 fechou em 2026-07-05 (*"cada campo é load-bearing"*) e
  foi re-verificado pós-welds: mesma fórmula, 12 B em 2 colunas anônimas.
- **Tirar os sizes não é opção**: O-FMT-19 foi **refutado** — mata o decode paralelo e o O(1)
  do lazy. **Os byte-sizes SÃO o mecanismo de paralelismo.**
- **Hex é a decisão** (T-FMT-HEADER-BASE-HEX); base-94 colidiria com os separadores do meta.
- **A ordem das colunas é livre**: corpos byte-idênticos em qualquer permutação, variação total
  de 3 B (só a escolha de qual fica por último).
- **Perfil stream-ready custa 4 B**: `min_header=False` leva de 1 para **zero** as colunas que
  dependem de EOF.
- **O único campo grande removível são os NOMES** — 45% do header; `drop_names` leva 82 → 39 B,
  ao preço de a ordem virar o contrato.

Lab: [`1530`](2026-08-16/2026-08-16-1530-piso-do-header-e-fronteira-paralela/).

---

## 6. Paralelismo — os três lados

| | estado |
|---|---|
| **compressão** | **existe e é soldado** — `encode(parallel=N)` por coluna, saída **byte-idêntica** ao serial |
| **decode** | **não existe, mas não falta nada no formato** — provado por orquestração externa em 23 tabelas reais, com `src/tcf` intocado |
| **entrega / stream de encode** | **bloqueado**: o header exige sizes antes do body (V2-J, ADR-0018) — **defer 2.0**, já decidido |

**O header é o único coldstart.** Depois da linha 1, cada coluna é independente nos dois
sentidos.

Registrado e **não coberto por ticket nenhum**: o eixo *decode entregando enquanto o encode
não terminou* (produtor e consumidor concorrentes sobre o mesmo blob) — nomeado para o estudo
dedicado de serialização×paralelismo, que o owner definiu como trabalho próprio, em etapas.

---

## 7. O que está aberto, por tamanho

| item | tamanho | bloqueio |
|---|---|---|
| **`T-8H-UM-CANDIDATO-SO`** | **99,986%** do overhead do `.8H` | nenhum — **não auditado ainda** |
| **`T-DATETIME-TIPO`** | 7,13× (split num datetime real) | falta caracterizar |
| **cross-dict** (A2) | 21,2% em same-domain com k grande | escopado `.9` |
| **B1 `T-META-NAO-DECLARA-MODO`** | gate do Grupo A | mudança de formato |
| **Grupo A `T-UM-CAMINHO-SO`** | **2,3%** do corpus | B1 |
| **`T-NUMERO-SPEC`** | 1,9×–3,0× em 3 regimes | — |
| **B2 `T-SPEC-SEM-CARIMBO`** | −4 B por wire | desenhado, falta weld |
| **B3 O-FMT-14** (header derivável) | o único lever grande do header | feature de contrato |

**Fechados neste ciclo**: os três defeitos silenciosos do Grupo C (`T-META-COLISAO-NOME-POSICIONAL`,
`T-NATURE-IGNORADA-CALADA` §1/§2, `T-POLARIDADE-COME-NOME`), com wire byte-idêntico e prova
vermelho→verde reproduzível ([lab `2020`](2026-08-16/2026-08-16-2020-verificacao-dos-welds-C1-C2-C3/)).
