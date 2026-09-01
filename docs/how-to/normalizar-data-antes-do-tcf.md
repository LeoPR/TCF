# Como entregar data ao TCF

> **Para quem produz o dado**, não para quem mexe no TCF. Nada aqui exige código novo no
> formato: é o que dá **mais retorno por menos esforço** em coluna de data.

## A regra, em uma linha

**Escreva a data como 10 caracteres: `YYYY-MM-DD`.** Hífen, ano de 4 dígitos, zero à
esquerda, sem sufixo de fuso.

```
2026-01-31        ✅
20260131          ❌ sem hífen
2026-1-31         ❌ sem zero à esquerda
2026-01-31Z       ❌ sufixo de fuso
31/01/2026        ❌ outra grafia
26-01-31          ❌ ano de 2 dígitos
```

### Por que a regra é em **caracteres** e não "use ISO 8601"

Porque *"conforme ISO 8601"* não especifica nada: a ISO 8601 admite a forma **básica**
(`20260131`) e a **estendida** (`2026-01-31`), e a escolha fica "por acordo entre as
partes" ([W3C NOTE-datetime](https://www.w3.org/TR/NOTE-datetime)).

O nome certo do que queremos é **RFC 3339 `full-date`**, que tem gramática fechada
([RFC 3339 §5.6](https://www.rfc-editor.org/rfc/rfc3339.html)). É a mesma produção que o
TOML e o JSON Schema citam.

E *"use o canônico do `xs:date`"* também não resolve: a canonicalização do XSD manda
**anexar o fuso quando ele existe**, então `2026-01-31`, `2026-01-31Z` e `2026-01-31+02:00`
sobrevivem os três.

---

## A boa notícia: a maioria já emite isso sem você fazer nada

Com tudo no default, **estes já emitem `YYYY-MM-DD`**:

| | |
|---|---|
| **bancos** | PostgreSQL · MySQL · MariaDB · SQL Server (tipo `date`) · SQLite (`date()`) · DuckDB |
| **linguagens** | Python (`str(date)` ≡ `isoformat()`) · Java (`LocalDate.toString()`) · Rust (`chrono::NaiveDate`) · Go (`time.DateOnly`) · JS `Temporal.PlainDate` |
| **formatos** | TOML (`local-date`) · XSD (`xs:date`, sem fuso) |

## As exceções, nominalmente: porque não são periféricas

### ⚠️ Oracle: precisa de ação, e ajustar o banco **não basta**

O default vem do território (`NLS_TERRITORY` → `NLS_DATE_FORMAT`), e em US/UK dá
`31-JAN-26`, **com ano de 2 dígitos** (`RR`) e **mês por extenso no idioma do cliente**
(`MON`). Pior: o parâmetro do servidor é sobrescrito pelo `NLS_LANG` do cliente
JDBC/OCI, então **dois clientes veem grafias diferentes da mesma coluna**.

```sql
TO_CHAR(col, 'YYYY-MM-DD')     -- explícito
DATE '2026-01-31'              -- literal ANSI, imune ao NLS
```

E um detalhe que importa: o `DATE` do Oracle **sempre carrega hora internamente**. O
default apenas não a imprime.

### ⚠️ .NET: a **ordem dos campos** muda com a cultura

`DateOnly.ToString()` sem cultura dá `5/1/2021` em `en-US`, `01/05/2021` em `fr-FR`,
`2021/05/01` em `ja-JP`. Não é só o separador: **é a ordem**, que é exatamente a fonte de
ambiguidade.

```csharp
d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)
```

### ⚠️ JavaScript `Date`: o fuso muda o **valor**, não só a grafia

O `Date` legado não tem date-only. `toISOString()` converte para UTC, `toDateString()` usa
hora local: **a mesma instância pode render dias diferentes**. Use `Temporal.PlainDate`
onde estiver disponível, ou formate explicitamente.

### ⚠️ JSON: não tem tipo de data, e o de-facto é **timestamp**

A [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) define 4 primitivos, nenhum
temporal. Na prática, `JSON.stringify` de um `Date` chama `toISOString()` e produz
`2026-01-31T00:00:00.000Z`, **datetime, não date**.

> Se a coluna é conceitualmente uma **data**, converta para `YYYY-MM-DD` **explicitamente**
> antes de serializar. Deixar o default do ecossistema agir entrega 24 caracteres onde 10
> bastam, e ainda arrasta um fuso que você não queria.

E `"format": "date"` no JSON Schema **não valida por padrão**: o vocabulário
Format-Annotation exige que a asserção fique desligada, então `31/01/2026` passa.

### ⚠️ CSV: não existe default

A [RFC 4180](https://www.rfc-editor.org/rfc/rfc4180.html) é puro texto; a grafia é 100% do
produtor. Planilhas escrevem conforme a configuração regional da máquina.

### ⚠️ YAML: depende da **versão**, não do locale

`2026-01-31` vira `date` no YAML 1.1 (tag `timestamp`) e **string** no 1.2, que não tem tag
temporal.

---

## As outras três coisas que valem tanto quanto a grafia

Medidas nos labs, e nenhuma custa código:

### 1. Uma grafia só por coluna

Misturar formatos degrada muito: 25% dos valores em `DD/MM/YYYY` dentro de uma coluna ISO
derrubou o ganho de **−93,7% para −5,5%**.

### 2. Ordene a coluna, se a ordem não importar

A mesma coluna de datas espalhadas, ordenada, comprimiu **8,4×** melhor. É o maior efeito
isolado que medimos fora da escolha de grafia.

> Cuidado: o TCF tem `sort_by`, mas ele é **order-free**: o decode devolve o mesmo conjunto de
> linhas, e a ordem original não volta. Só use quando a ordem for irrelevante.
>
> E ele não garante que vai ordenar. Desde a 0.8.4 a ordenação é um candidato, e o encoder só
> a emite quando ela encolhe o wire, o que numa tabela de várias colunas independentes da chave
> frequentemente não acontece. Se você quer a coluna de datas ordenada para ganhar os 8,4× desta
> página, ordene os dados **antes** de encodar, em vez de contar com o kwarg.

### 3. Prefira o passo regular, se você controla a geração

Coluna de datas com passo constante (diário, semanal, mensal) comprime em **~22 bytes
independentemente do tamanho**, porque o mecanismo de sequência do TCF a colapsa inteira.
Irregularidade custa **38×** contra regularidade, no mesmo formato e mesmo comprimento.

---

## O que acontece se você não seguir

**Nada quebra.** O TCF trata data como string e faz round-trip byte-exato de qualquer
grafia, inclusive das que não são data nenhuma. Você só comprime menos.

E se um dia houver um spec de data no TCF, ele entrará como **candidato**: quando o palpite
dele não ajudar, o wire cai de volta no que seria hoje. Medido: **nunca pior que hoje**.

## Uma armadilha silenciosa

`datetime.date.fromisoformat()` do Python **aceita mais do que emite**: `20191204` e
`2021-W01-1` entram e saem como `2019-12-04` e `2021-01-04`.

Isso é **normalização, não round-trip**: a grafia original se perde ali, antes de o TCF ver
qualquer coisa. Se o seu pipeline passa por essa função, o dado já chega normalizado (bom
para compressão), mas não conte com o TCF para devolver a forma que você digitou.

O MySQL faz algo parecido: aceita `2012@12@31`, mas marca como *deprecated* e emite
*warning*.

---

## Casos de borda que a regra dos 10 caracteres **não** cobre

Anos fora de `0000` a `9999`. O `chrono` do Rust emite `-0001-01-01` e `+10000-12-31`, e o
Java tem a mesma borda. O Python nem representa esses anos.

Se a sua fonte tem datas assim, **declare o comportamento explicitamente**: não há
convenção comum a seguir.

---

## Fontes

[RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html) ·
[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) ·
[RFC 4180](https://www.rfc-editor.org/rfc/rfc4180.html) ·
[PostgreSQL DateStyle](https://www.postgresql.org/docs/current/runtime-config-client.html) ·
[MySQL DATE](https://dev.mysql.com/doc/refman/8.4/en/datetime.html) ·
[SET DATEFORMAT](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-dateformat-transact-sql) ·
[Oracle NLS_DATE_FORMAT](https://docs.oracle.com/en/database/oracle/oracle-database/23/refrn/NLS_DATE_FORMAT.html) ·
[.NET DateOnly.ToString](https://learn.microsoft.com/en-us/dotnet/api/system.dateonly.tostring) ·
[TOML 1.0.0](https://toml.io/en/v1.0.0) ·
[YAML 1.2.2](https://yaml.org/spec/1.2.2/) ·
[JSON Schema 2020-12](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-validation-01)

Os números de compressão vêm dos labs
[`2026-08-07-2311`](../../experiments/lab/dirty/2026-08/2026-08-07/2026-08-07-2311-datas-exploracao/) ·
[`2026-08-08-0016`](../../experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-0016-data-lazy-iso/) ·
[`2026-08-08-0235`](../../experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-0235-data-alvos-e-declaracao/) ·
[`2026-08-08-1854`](../../experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-1854-custo-da-ambiguidade/).
