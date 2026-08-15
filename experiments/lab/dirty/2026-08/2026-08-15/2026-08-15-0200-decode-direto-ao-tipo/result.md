# Resultado — decode direto ao tipo: a proposta se sustenta, com uma fronteira e um ruído

3 casos, **0 falhas**. Orienta, não fecha.

## Os números

| caso | n | RT str | volta obj | hoje (ns/val) | direta (ns/val) | economia |
|---|---:|---|---|---:|---:|---:|
| diária | 200 | ✓ | ✓ | 6690 | 7084 | **−5,9%** |
| diária | 2000 | ✓ | ✓ | 9030 | 7445 | **17,5%** |
| com literal | 500 | ✓ | ✓ | 7782 | 6278 | **19,3%** |

"Hoje" = `decode → string` + o cliente re-parseia (`date.fromisoformat`). "Direta" =
`decode_value` devolve o **objeto** — nada se serializa e nada se re-parseia.

**A economia é sobre o decode completo** (com header, corpo, tudo) — não sobre a conversão
isolada. 17–19% do decode inteiro é o que as duas pontas cortadas valem.

**O −5,9% do caso pequeno é ruído de dev-run**: a rota direta faz estritamente menos trabalho
(mesmo decode, menos um `isoformat` e menos um `fromisoformat` por valor), então não há
mecanismo para ela ser mais lenta — em n=200 a variância do melhor-de-5 é maior que a
diferença. Declarado, não escondido.

## O fato de código que sustenta a proposta do owner

`data_iso.py:107` — `return _FROM_ORD(int(payload)).isoformat()`. **O objeto `date` já existe
no meio do decode e é jogado fora** ao serializar. O cliente então re-parseia. A proposta corta
as duas pontas, e o desenho dela cabe na válvula que já existe: o protótipo é um spec cujo
`decode_value` devolve o objeto — **9 linhas, `src/tcf` intocado**.

## A resposta a "o encode já tem algo assim?"

**Sim — o decode já transforma, soldado.** `decoder.py::_cast_tipo`: *"os literais do core
viram o tipo TIPADO"* — a rota tipada converte string→`int`/`float`/`bool` **dentro do decode**
hoje. A proposta é estender a mesma lógica aos specs de grafia, opt-in.

E o simétrico do encode: a rota tipada **aceita** objetos nativos (`int`/`float`/`bool`) e o
`date` como objeto é **recusado** (`HierarchicalError`, medido em 2026-08-15). Pela sua regra
(*"prefiro que ele siga as regras que já decidimos do date"*), **continua assim**: a entrada é
string pré-formatada por recomendação de manual. Nada a mudar no encode.

## A união na saída — e o precedente que já a decidiu

No caso com a não-canônica no meio, a saída-objeto é `['date', 'str']` — o literal continua
string. Isso **não é decisão nova**: é o **CONTRATO UNIÃO** que o ADR-0039 já fixou para o
lazy bool (*"o decode emite lista mista `[bool | None | str]` — decisão do owner: lazy =
default"*). O decode direto ao tipo herda o contrato pronto.

## Análise crítica — é exagerado?

**Não. E cada ressalva sua já tem o mecanismo correspondente:**

| a sua ressalva | o mecanismo |
|---|---|
| *"só se for extremamente barato"* | é **negativo em custo**: a rota direta faz menos trabalho que a de hoje. E o leitor é o nativo (`fromordinal`), 149 ns |
| *"não importar libs caras"* | `datetime` da stdlib, que o spec **já** importa |
| *"padronizar antes; não virar datatransform portátil"* | a linha vermelha: o parâmetro escolhe o **TIPO** de saída (o objeto nativo), **nunca uma grafia** — `ordinal → "31/01/2026"` é transformação nova e fica fora |
| *"se for feito em outra linguagem, não inflar o núcleo"* | o parâmetro é da **API do host**, não do formato: **o wire não muda um byte**. Cada host entrega o objeto nativo *dele* (Rust: `chrono::NaiveDate`); host que não implementa fica na string — **droppable por construção** |

**Os cuidados que eu acrescentaria** (e são pequenos):

1. **O ganho é % do decode, não do pipeline do cliente** — se o cliente faz muito mais que
   converter, os 17–19% diluem. É otimização de borda, e deve ser vendida como tal.
2. **Em coluna pequena é ruído** — o FLOOR de sempre resolve: opt-in, nunca default.
3. **O RT muda de contrato quando a saída é objeto** (tipo+valor, não grafia) — mas isso é
   exatamente o plano 5 da sua formulação, e o modo string continua sendo o default e o
   contrato byte-exato.

## O desenho que fica (sem weld, registrado)

```python
decode(w, nature=SPEC_DATA_ISO)                 # hoje: strings — o default, RT byte-exato
decode(w, nature=SPEC_DATA_ISO, saida="date")   # opt-in: objetos da lib nativa do host
```

No protótipo o veículo foi um spec com id próprio (limitação de lab); num weld real o kwarg
escolheria a saída **sem tocar o wire** — o mesmo wire `:dt` serve os dois modos.
