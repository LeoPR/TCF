# Proveniência das entradas

**Todas sintéticas-realistas, construídas para exercitar as bordas de especiais — viés
DECLARADO** (material de forma/decisão, não medida de ganho; nomes/e-mails/coordenadas
fictícios, domínio `acme.com.br` reservado para exemplo).

| entrada | origem | por que é realista | viés |
|---|---|---|---|
| `inputs/01-clientes-api.json` | escrita à mão, JSON **padrão** | resposta típica de API de cadastro: null em campo opcional, registro sem `endereco`, `{}` vazio, arrays ragged | construída p/ conter TODAS as irregularidades de presença |
| `inputs/02-telemetria-jsonlike.json` | escrita à mão, gramática **declarada** JSON+`NaN`/`Infinity` | `json.dumps(allow_nan=True)` do Python emite exatamente isto; NaN de sensor falho e Infinity de divisão-por-zero são ocorrências comuns de telemetria | idem; densidade de especiais maior que o típico |
| `inputs/03-sensores-tabular.csv` | export `str()` da origem tipada (`SENSORES` em `run.py`) | é o CSV que um pipeline Python/pandas exporta: `nan`/`inf` soletrados, `None` de null e `None` literal INDISTINGUÍVEIS — a dupla-stringificação real | 6 linhas (minúsculo; custo relativo do kind-channel não representa volume) |

A origem TIPADA dos sensores (floats de verdade, null de verdade) vive em `run.py`
(`SENSORES`) e está renderizada em `intermediates/01-sensores-origem-tipada.txt`;
`run.py` **assert**a que o CSV é exatamente o `str()` dela.
