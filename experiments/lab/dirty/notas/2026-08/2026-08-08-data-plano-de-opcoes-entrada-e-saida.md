# Data — plano de opções: onde o TCF se mete na entrada e na saída

**2026-08-08 · plano de decisão. Nenhum código mexido.**

Owner: *"preciso de um plano de opções pra decidir onde a gente se mete na entrada e saída
(…) estou indeciso."*

---

## A observação que dissolve a indecisão: **o bool já faz isso**

A pergunta parece nova, mas o TCF já a respondeu uma vez — para `bool` — e a resposta está
soldada e ninguém acha estranha. Conferido rodando:

| entrada | wire | volta | contrato |
|---|---|---|---|
| `[True, False]` | `#TCF.8b16↵qA==` — **bits** | `bool` | **RT semântico** |
| `["true","false"]` | `#TCF.8B16↵…` | `str`, byte-exata | **RT textual** |
| `["TRUE","1"]` | `#TCF.8B16↵…` | `str`, byte-exata | **RT textual** |

Repare no que acontece no bool nativo: **o usuário mandou `True` e o fio não guarda nem
`true`, nem `True`, nem `1` — guarda bits.** A grafia é escolha do formato, o usuário nunca
a vê, e a volta é `bool`.

> **Os dois contratos coexistem sem ambiguidade porque o TIPO DE ENTRADA decide qual vale.**

É exatamente a intuição levantada (*"algumas linguagens obrigam True/true/TRUE/1, mas o TCF
converte pelo tipo e a linguagem aceita"*). Ela está certa, e já é o desenho vigente.

**Data seria idêntica em estrutura.** A única diferença é que o Python não tem `date`
primitivo — tem classe. Mas `bool` também é objeto em Python, e isso não atrapalhou nada.

---

## O que o TCF confia — a fronteira, dita com precisão

| camada | quem garante | o TCF revalida? |
|---|---|---|
| o valor é uma data | **o dataset** (ou o SQL a montante) | **não** |
| a grafia é aquela declarada | **o produtor** | **não** — só classifica: aproveita ou não |
| o wire é canônico | **o TCF** | **sim** — é o único lugar onde ele julga |

A observação sobre o SQL está certa e vale registrar: **o `DATE` do SQL já é binário lá
dentro**; o que o `SELECT` mostra é uma *conversão de saída*. Então "data como string" nunca
foi a forma de armazenamento — foi sempre a forma de **transporte**. O TCF recebe a forma de
transporte e a comprime; a forma de armazenamento dele é outra (o wire).

Isso reenquadra a pergunta: **o TCF não está escolhendo "como guardar data" — está
escolhendo o que fazer com uma tradução que já aconteceu antes dele.**

---

## As cinco opções, e o que cada uma custa

| | opção | entra | sai | grafia preservada? | onde mexe |
|---|---|---|---|---|---|
| **A** | nada (hoje) | `str` | `str` byte-exata | sim | — |
| **B** | **pré-filtro orientado** | `str` já sadia | `str` byte-exata | sim | **fora do TCF** — guia/ferramenta |
| **C** | **spec lazy declarado** | `str` + `nature=SPEC_DATA_*` | `str` byte-exata | sim | `natures/` |
| **D** | spec com sniff | `str` | `str` byte-exata | sim | `natures/` + detector |
| **E** | **tipo data nativo** | `date` | `date` | **não** — e não precisa | `_tipo_single_col` + tag |

### O que já foi medido sobre cada uma

- **A** — nunca é ótima. Em 8 regimes, o `iso` cru venceu em 1 (`agrupado`), e por 2 bytes.
- **B** — é a opção **de maior retorno por menor esforço**: zero código no TCF. Se o dado
  chega em ISO regular, o core já entrega **−93,7%** sem nature nenhuma… **desde que a
  transformação aconteça antes.** É aqui que a orientação vale dinheiro.
- **C** — medido: RT 19/19 mesmo com spec errando 100%; teto do prejuízo **+4,9%**; header
  custa **10 B** fixos. Funciona.
- **D** — o sniff **não substitui declarar** (senão o decode não inverte). É front-end de C,
  não opção separada. E errar o palpite custa bytes, nunca dado — então pode ser preguiçoso.
- **E** — **não existe hoje**: `encode([date(2026,1,1)])` é `fail-loud`. É a opção que a
  última ideia do owner descreve, e é a que tem o precedente mais forte (o bool).

---

## A recomendação de pipeline

```
      SQL / JSON / CSV
            │
            ▼
   ┌─────────────────────┐   O dado ainda é do produtor. É AQUI que se ganha
   │  1. NORMALIZAÇÃO    │   mais por menos esforço — e é fora do TCF.
   │     (orientada)     │
   └─────────────────────┘
            │  str em UMA grafia estável, ou `date` nativo
            ▼
   ┌─────────────────────┐   Opt-in. Classifica, transforma, escapa o que não
   │  2. SPEC / PRÉ-TX   │   casa. Não valida, não corrige.
   └─────────────────────┘
            │
            ▼
   ┌─────────────────────┐   O que já existe. Nada muda aqui.
   │  3. CORE            │
   └─────────────────────┘
```

### O guia de normalização (etapa 1) — o que ele diria

| origem | recomendação | por quê |
|---|---|---|
| **SQL `DATE`** | já sai certo em Postgres/MySQL/MariaDB/SQL Server/SQLite/DuckDB. **Oracle exige `TO_CHAR`** | o Oracle usa `DD-MON-RR` por locale — ano de 2 dígitos, mês por extenso — e o `NLS_LANG` do CLIENTE sobrescreve o servidor |
| **JSON** | **converta para `YYYY-MM-DD` explicitamente** | o JSON não tem tipo de data, e o de-facto (`JSON.stringify` → `toISOString`) dá **timestamp** com 24 chars onde 10 bastam, e um fuso indesejado |
| **CSV** | `YYYY-MM-DD`, e **uma grafia só por coluna** | a RFC 4180 não tem default; e 25% em BR dentro de ISO derruba o ganho de −93,7% para −5,5% |
| **.NET** | `ToString` com `CultureInfo.InvariantCulture` | a `CurrentCulture` muda a **ordem dos campos**, não só o separador |
| **qualquer** | **ordene a coluna se a ordem não importar** | `espalhado-ord` com `delta-dias` fez **8,4×** contra o mesmo dado desordenado |

> **Correção (levantamento 2026-08-08):** a recomendação original dizia *"use ISO"*. Não
> basta — a ISO 8601 admite `20260131` **e** `2026-01-31`. O nome certo é **RFC 3339
> `full-date`**, e a regra tem de ser escrita **em caracteres**, não por referência a tipo.
> Guia: [`docs/how-to/normalizar-data-antes-do-tcf.md`](../../../../docs/how-to/normalizar-data-antes-do-tcf.md).

Essas quatro linhas são a *matéria* que o owner pediu. Repare que **nenhuma exige código no
TCF** — e a última (ordenar) tem o maior efeito isolado que medimos fora do alvo.

### E o pré-filtro dentro do TCF

A ideia de *"ter essa etapa no pré-filtro, pra não confundir o desenvolvedor"* encaixa: o
`nature=`/`nature_per_col=` **já é** esse pré-filtro, e já é opt-in. Não é preciso desenhar
uma etapa nova — é preciso um `SPEC_DATA_*` no registry existente.

---

## A opção E merece mais crédito do que parece

*"se é data cuja origem nativa é tipo data mesmo, basta o TCF decodificar da melhor forma em
tipo data, mesmo que não fique igual"*

Isso soa como perda, e não é — é **o mesmo contrato do bool**, que já existe e não incomoda
ninguém. Três consequências concretas:

1. **Some a ambiguidade BR/US.** Não há grafia de entrada a preservar, então não há o que
   desambiguar. O problema que consumiu duas rodadas de análise **desaparece**.
2. **Some a declaração de grafia.** Os 10 B do header não são necessários: a tag de tipo
   (índice 6) já diz "isto é data", e a grafia interna é escolha do TCF.
3. **Libera o melhor alvo sem restrição.** Sem grafia a preservar, o TCF pode usar o alvo que
   comprimir mais em cada regime — inclusive os que destroem a grafia (`ordinal-denso`), que
   hoje pagam header.

O custo real é um só, e é honesto: **quem consome tem de aceitar a grafia que o TCF devolver**
— ou reformatar. Exatamente como quem consome `bool` aceita `True` e formata como quiser.

---

## O plano, em ordem de retorno por esforço

| # | passo | esforço | retorno | mexe em `src/tcf`? |
|---|---|---|---|---|
| 1 | **Escrever o guia de normalização** (as 4 linhas acima, com os números medidos) | baixo | alto — vale para todo dado, sem código | **não** |
| 2 | **`SPEC_DATA_ISO` no registry** | baixo — o molde e a encanação existem | −93,7% em coluna limpa; +4,9% no pior caso | sim, aditivo |
| 3 | **Tipo data nativo (opção E)** | médio — tag nova + escolha de alvo | dissolve ambiguidade e declaração | sim |
| 4 | os outros `SPEC_DATA_*` (BR, US, compacto) | trivial — 4 linhas cada | breadth | sim |
| 5 | sniff como front-end | baixo | ergonomia | não (é gadget) |

**Os passos 2 e 3 não competem** — são os dois contratos do bool, e o tipo de entrada decide
qual vale. Fazer um não impede nem atrasa o outro.

---

## A pergunta que sobra pro owner

Só uma, e é sobre a **saída** da opção E:

> Quando `date` nativo entra e `date` nativo sai, ninguém pergunta nada. Mas se alguém quiser
> **texto** na saída, quem escolhe a grafia — o TCF (ISO fixo) ou o consumidor?

O precedente do bool diz: **o TCF devolve o tipo, e formatar é do consumidor.** Se for pra
seguir o precedente, não há decisão a tomar — e isso é bom sinal.

---

## O levantamento externo — feito

21 itens (bancos, linguagens, formatos), 10 correções na verificação. Incorporado acima e no
[guia](../../../../docs/how-to/normalizar-data-antes-do-tcf.md).

**Sim, existe um default de fato**: `YYYY-MM-DD` (RFC 3339 `full-date`) é o que emitem, sem
tocar em nada, PostgreSQL · MySQL · MariaDB · SQL Server · SQLite · DuckDB · Python · Java ·
Go · Rust/chrono · `Temporal.PlainDate` · TOML · `xs:date`.

**As exceções não são periféricas** e exigem ação na ponta: **Oracle** (locale, ano de 2
dígitos, e o cliente sobrescreve o servidor) e **.NET** (a cultura muda a ordem dos campos).
E **JSON/CSV/YAML não têm default nenhum** — no JSON o de-facto do ecossistema é timestamp,
não date.

O que **não** dá pra recomendar, e o levantamento foi explícito: confiar no `format:"date"`
do JSON Schema (a asserção fica desligada por padrão), no default do CSV (não existe), ou no
default do JSON (é timestamp).
