# O caminho do dado até o TCF: arquitetura, com data como caso

**Status**: rascunho 2026-08-08. Escrito durante o estudo de **data**, mas o esqueleto vale
para qualquer tipo com grafia (decimal, timestamp, duração, moeda). Complementa a
[taxonomia de naturezas](data-natures-taxonomy.md), que classifica o dado pelo
**comportamento**; aqui o eixo é o **caminho**.

---

## Por que este documento existe

O TCF é o penúltimo elo de uma cadeia longa. Quando um valor chega nele, **ele já foi
reescrito três ou quatro vezes**, e quase nada disso foi decidido pensando em compressão.

O erro que este documento tenta evitar é raciocinar como se o TCF recebesse "a data". Ele
não recebe: recebe **o resultado de uma sequência de traduções**, cada uma feita por um
componente que tinha outra prioridade.

---

## O caminho completo

```
  ┌── ARMAZENAMENTO ─────────────────────────────────────────────────────────┐
  │  SQL DATE (binário)   Parquet int32   CSV texto   JSON string   log linha │
  └──────────┬───────────────────────────────────────────────────────────────┘
             │  ① o driver decide o que entrega: objeto nativo ou texto?
             ▼
  ┌── LINGUAGEM ─────────────────────────────────────────────────────────────┐
  │  date · datetime · Decimal · str · o tipo do runtime                      │
  └──────────┬───────────────────────────────────────────────────────────────┘
             │  ② a serialização escolhe a GRAFIA — e aqui entra locale
             ▼
  ┌── TRANSPORTE ────────────────────────────────────────────────────────────┐
  │  JSON · CSV · JSONL · Parquet · fila · corpo HTTP                          │
  └──────────┬───────────────────────────────────────────────────────────────┘
             │  ③ o parse do outro lado devolve string (quase sempre)
             ▼
  ┌── DATASET (+ schema) ────────────────────────────────────────────────────┐
  │  list[str] · dict[str, list[str]] · e a DECLARAÇÃO opcional do spec        │
  └──────────┬───────────────────────────────────────────────────────────────┘
             │  ④ ⇽ é AQUI que o TCF começa a poder fazer alguma coisa
             ▼
  ┌── TCF ───────────────────────────────────────────────────────────────────┐
  │  pré-tx (nature) → core (OBAT + HCC + bN) → wire                          │
  └──────────┬───────────────────────────────────────────────────────────────┘
             │  ⑤ decode devolve exatamente o que entrou
             ▼
  ┌── CONSUMIDOR ────────────────────────────────────────────────────────────┐
  │  e quase sempre mais UMA tradução, pro formato que ele precisa            │
  └──────────────────────────────────────────────────────────────────────────┘
```

## Onde a data é reescrita, fronteira por fronteira

| # | fronteira | quem decide | o que pode mudar |
|---|---|---|---|
| 1 | armazenamento → driver | driver/ORM | tipo nativo **ou** texto; e **qual** texto |
| 2 | driver → linguagem | a lib | `date`, `datetime`, `str`, `Decimal` |
| 3 | **linguagem → serialização** | `str()`, `isoformat()`, `strftime`, `toISOString` | **a grafia**, e é aqui que o locale entra |
| 4 | serialização → transporte | o formato | JSON vira string; CSV vira texto; Parquet vira int |
| 5 | transporte → parse | o parser | quase sempre devolve **string** |
| 6 | parse → dataset | o pipeline | pode normalizar, e pode **declarar o spec** |
| 7 | dataset → TCF | `encode()` | pré-tx opcional |
| 8 | TCF → decode | `decode()` | devolve o que entrou (contrato) |
| 9 | decode → consumidor | a aplicação | mais uma tradução |

**Nove fronteiras. O TCF ocupa duas (7 e 8).** As outras sete já aconteceram, ou vão
acontecer depois, e nenhuma pergunta nada a ele.

---

## O filtro: o que de fato chega no TCF

Das nove fronteiras, **só duas coisas atravessam** e mudam o que o TCF consegue fazer:

### A. A **grafia** que sobrou (decidida na fronteira 3)

O TCF vê caracteres. Se a fronteira 3 emitiu `2026-01-31`, ele tem 10 chars com estrutura
repetida. Se emitiu `2026-01-31T00:00:00.000Z`, tem 24, e 14 deles são constantes que não
carregam informação nenhuma naquela coluna.

### B. A **ordem e a regularidade** da coluna (decididas na fronteira 1)

Uma consulta com `ORDER BY` e outra sem produzem o mesmo conjunto de datas e **colunas
completamente diferentes** do ponto de vista de compressão. Medido: a mesma coluna
espalhada, ordenada, comprimiu **8,4×** melhor.

> **Tudo o mais é ruído para o TCF.** Se o `DATE` era binário no disco, se passou por ORM,
> se o JSON foi minificado, nada disso o alcança. Ele vê a grafia e a ordem.

Este é o filtro que o resto do documento aplica: **só interessa o que muda A ou B**.

---

## Os dois eixos de impacto

### Eixo 1: congestão (CPU do pipeline)

| onde | custo medido | quem paga |
|---|---|---|
| coluna **suja** (valores que não casam a grafia) | **15× mais CPU** no encode | o TCF |
| o **FLOOR** materializando candidatos | **58% do encode** | o TCF |
| normalizar antes (`strptime`) | 53% do encode | o pipeline |
| normalizar antes (`fromisoformat`, C) | 3,2% do encode | o pipeline |
| o fluxo total, normalizando | **1,81×** o tempo | dividido |

**A leitura honesta:** normalizar custa pouco (15% do fluxo); o encode custa muito (71%); e
dentro do encode, mais da metade é o FLOOR comparando candidatos. **Jogar a normalização
pra fora do TCF não tira o ônus do fluxo, só o tira da conta do TCF.**

E há um efeito que costuma passar batido: **dado sujo custa CPU, não só bytes**. Uma coluna
com 10% de valores fora da grafia levou 15× mais tempo para encodar do que a mesma coluna
limpa, porque o lixo quebra os padrões que o OBAT persegue.

### Eixo 2: compressão

| o que a fronteira decidiu | efeito medido |
|---|---|
| grafia com separador (`2026-01-31`) vs sem (`20260131`) | o sem-separador é **8% menor**: o separador quebra o afixo |
| grafia **única** por coluna vs misturada | 25% de outra grafia derruba o ganho de −93,7% para **−5,5%** |
| coluna **ordenada** vs espalhada | **8,4×** |
| passo **regular** vs irregular | **38×**, no mesmo formato e comprimento |
| date-only vs timestamp com `T00:00:00Z` | 10 chars contra 24 |

Repare que **as três maiores alavancas (ordem, regularidade, grafia única) não são sobre
"qual formato"**, são sobre disciplina da coluna. A escolha do formato é a menor das
quatro.

---

## Casos particulares: as combinações que aparecem de verdade

### 1. SQL → driver → dataset

O caminho mais limpo. Postgres/MySQL/MariaDB/SQL Server/SQLite/DuckDB emitem `YYYY-MM-DD`
por default. **Oracle é a exceção** e exige ação: o default por locale dá ano de 2 dígitos e
mês por extenso, e o `NLS_LANG` do *cliente* sobrescreve o servidor.

*Onde mexer*: na consulta (`ORDER BY` se a ordem não importar) e, no Oracle, no `TO_CHAR`.

### 2. API REST → JSON → dataset

O caminho mais comum e o mais degradado. **JSON não tem tipo de data**; o de-facto do
ecossistema (`JSON.stringify` → `toISOString`) produz **timestamp**, não date. Uma coluna
conceitualmente de datas chega com 24 caracteres, 14 deles constantes.

*Onde mexer*: na serialização, convertendo para date-only explicitamente. AWS/Smithy
padroniza em ISO 8601 date-time, bom para instante, desnecessário para data.

### 3. Planilha → CSV → dataset

O mais imprevisível. A RFC 4180 não define nada; a planilha escreve conforme a configuração
regional da máquina de quem exportou. É o caso em que a **grafia mista na mesma coluna**
aparece de verdade, e é justamente o que mais custa.

*Onde mexer*: na exportação, ou numa passada de normalização antes do dataset.

### 4. Parquet/Arrow → dataset

O caminho em que a data **já é um inteiro** (`date32` = dias desde a época). Convertê-la para
string ISO para depois o TCF reconvertê-la para ordinal é um ciclo perdido.

*Observação de arquitetura*: este é o caso onde o **tipo nativo** (hoje `fail-loud` no TCF)
teria o maior ganho, o dado já está na forma que o TCF quer.

### 5. Log/JSONL → dataset

Timestamp, não data. Alta regularidade quando o log é sequencial (medido: 0,31 B/valor),
péssima quando é esparso (11,68 B/valor). **Mesmo formato, mesmo comprimento, 38× de
diferença**, a regularidade domina tudo.

---

## Como transportar data hoje

Consolidando o levantamento (bancos, linguagens, formatos):

**`YYYY-MM-DD`, RFC 3339 `full-date`.** Não "ISO 8601", que admite também `20260131` e
deixa a escolha "por acordo entre as partes". A regra tem de ser escrita **em caracteres**:
10 chars, hífen, zero à esquerda, sem sufixo de fuso.

É o que já emitem por default: PostgreSQL · MySQL · MariaDB · SQL Server · SQLite · DuckDB ·
Python · Java · Go · Rust/chrono · `Temporal.PlainDate` · TOML · `xs:date`.

As exceções que exigem ação na ponta: **Oracle**, **.NET** (a cultura muda a ordem dos
campos), **JS `Date`** (o fuso muda o valor), e **JSON/CSV/YAML**, que não têm default.

Detalhe operacional em [`docs/how-to/normalizar-data-antes-do-tcf.md`](../how-to/normalizar-data-antes-do-tcf.md).

### E o formato compacto `YYYYMMDD`?: avaliação independente do TCF

Pergunta recorrente, e legítima: *"um SQL fazendo leitura massiva, pedindo `YYYYMMDD`, não
economizaria transmissão sem perder nada pra traduzir?"*. Avaliado abaixo **sem compromisso
com o TCF**, vale como prática de transporte.

**É padrão?** Sim. É o **formato básico** da ISO 8601 (o `YYYY-MM-DD` é o *estendido*). E é
usado em produção: o **AWS Signature V4** monta o credential scope como
`access_key/YYYYMMDD/region/service/aws4_request`, e o timestamp da assinatura é
`YYYYMMDD'T'HHMMSS'Z'`
([AWS API Reference](https://docs.aws.amazon.com/kms/latest/APIReference/CommonParameters.html)).
Note o uso: **assinatura e escopo**, não transporte de dado.

Aviso importante: a **RFC 3339 não admite a forma básica**, só a estendida. Então
`YYYYMMDD` é ISO 8601 válido e RFC 3339 inválido, e boa parte do ecossistema (JSON Schema
`format: date`, TOML, `xs:date`) segue a RFC.

**O que ele poupa, medido**: coluna de 200 000 datas num CSV/JSON:

| | ordenada (com `ORDER BY`) | espalhada |
|---|---:|---:|
| **cru** | **−18,2%** | **−18,2%** |
| gzip −6 | −1,9% | −7,1% |
| gzip −9 | −2,0% | −4,3% |
| brotli | **+0,9%** (fica *maior*) | −3,2% |

**O ganho de 18% vira 2–7% assim que o canal comprime, e pode virar negativo.** A razão é
direta: os separadores são altamente redundantes, e o compressor os come quase de graça.
Tirá-los remove bytes **compressíveis**, não os caros.

E as duas práticas compõem mal: no cenário ordenado, que é a recomendação de maior impacto,
a economia do compacto é a **menor** (1,9% sob gzip, negativa sob brotli).

**Custo de traduzir**: no consumidor, zero, `date.fromisoformat` aceita as duas formas e
custa o mesmo (162 ns × 161 ns por valor, medido). No produtor, formatar explicitamente
(`TO_CHAR`, `strftime`) tira o caminho default otimizado, **não medido aqui**, e é o lado
que decide se a troca vale.

**Onde o compacto é de fato a escolha certa:**

- **assinatura e escopo** (o caso do AWS SigV4): onde o valor é chave, não dado;
- **nome de arquivo e rotação de log**: `2026-01-31.log` × `20260131.log`: o compacto ordena
  igual e não colide com separadores de caminho;
- **transporte de texto NÃO comprimido**, se existir: aí os 18% são reais;
- **campo de largura fixa** (COBOL, NACHA, arquivos posicionais): onde o separador não cabe.

**Onde não vale:**

- transporte comprimido (a maioria): 2–7%, e o `ORDER BY` dá muito mais;
- transporte binário (Parquet, Arrow, protocolo nativo): a data já é `int32`, nenhuma
  grafia se aplica;
- qualquer lugar que valide por RFC 3339: o compacto é rejeitado.

---

## O que isto sugere para os próximos tipos

O esqueleto acima não é sobre data. Para qualquer tipo com grafia, as mesmas perguntas:

1. **Qual fronteira decide a grafia?** (quase sempre a 3, e quase sempre com locale envolvido)
2. **Existe um default de indústria?** Se existir, o guia é "use esse" e a maioria já está
   conforme.
3. **O que a grafia esconde?** Constantes que não carregam informação naquela coluna
   (o `T00:00:00Z` da data; os separadores de milhar do decimal; o `+55` do telefone).
4. **A ordem/regularidade da coluna importa mais que a grafia?** Em data, sim, por muito.
   Vale checar antes de investir em spec.

Os candidatos imediatos, pela mesma lente:

| tipo | fronteira crítica | o que a grafia esconde | tem default de indústria? |
|---|---|---|---|
| **timestamp** | 3 (locale + fuso) | fuso constante, precisão não usada | RFC 3339 `date-time`, sim |
| **decimal / moeda** | 3 (separador decimal por locale!) | separador de milhar; casas fixas | **não**, e o `Decimal` é `fail-loud` no TCF hoje |
| **duração** | 3 | unidade constante | ISO 8601 `PnYnMnD`, pouco usado |
| **telefone / doc** | 1 ou 3 | máscara | E.164 para telefone, sim |

O **decimal** merece atenção antes do timestamp: é o único da lista sem default de indústria
(o separador decimal muda com locale, `1.234,56` × `1,234.56`), e é o tipo que existe
justamente para **não** virar float.

---

## O que este documento não faz

- Não recomenda implementação. É arquitetura; as decisões estão nos tickets e ADRs.
- Os números citados vêm dos labs de data de 2026-08-07/08 e valem para **aquelas** colunas
  sintéticas. Ordem de grandeza, não constante universal.
- Não cobre fuso horário, horário de verão, nem calendários não-gregorianos.
