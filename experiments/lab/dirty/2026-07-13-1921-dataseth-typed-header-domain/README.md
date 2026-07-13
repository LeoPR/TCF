# 2026-07-13-1921 - DatasetH: dominio tipado no header

**Status**: pesquisa/medido, sintetico. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Plano**: [DatasetH - hierarquia completa e escalares especiais](../notas/dataseth-hierarquia-completa-plano.md).
**Hipotese**: H-HIER-SCALAR-01, alternativa B (dominio tipado + indices `bN`).

Este lab testa a ideia de declarar no header que um indice representa um
primitivo especial, por exemplo `null`, e deixar o corpo transportar apenas
indices. Ele nao modifica `src/tcf`, nao define a gramatica `#TCF.8H` e nao
cria `encode_json`.

## Pergunta e contra-prova

Um mapa ingenuo feito **depois** de converter valores em strings nao fecha
round-trip. `null` e a string literal `"null"` tornam-se ambos `"null"`, entram
no mesmo dominio e recebem o mesmo indice. O header nao consegue recuperar
qual ocorrencia era o valor primitivo.

Logo, `null=<indice>` so e lossless quando pelo menos uma das duas condicoes
vale antes da indexacao:

1. o dominio e tipado, com entradas distintas para `(null)` e
   `(string, "null")`; ou
2. cada ocorrencia carrega um kind index separado, e os payloads comuns
   continuam no canal string.

## Variantes exercitadas

| variante | header | corpo | alcance observado |
|---|---|---|---|
| `HDOM` | dominio inteiro de atomos tipados, por exemplo `z,s4:6e756c6c,q` | indices `b1`/`b2`/`b4` packed | dominio total de ate 16 valores distintos |
| `HK` | mapa pequeno de kinds ativos (`s,i,d,t,f,z,q,p,m`) | indices de kind packed + `tcf.encode(list[str])` para payloads comuns | strings de alta cardinalidade, pois o dominio de kinds continua pequeno |
| `V` | nenhum dominio compartilhado | tag por folha/ocorrencia | referencia comparativa per-instance |

`HDOM` e a forma direta da ideia `tipo -> index_ref`. `HK` e a alternativa
mais geral: o header registra que indice abre `null`, `NaN` ou infinito, mas
o TCF existente continua recebendo somente os payloads string/numero que
precisam de texto. Especiais nao carregam payload e nao podem colidir com a
string que os soletra.

As magics `#PROTO.HDOM` e `#PROTO.HK` sao deliberadamente externas. O stream
de indices e byte-packed, portanto esta no territorio de `bN`/V2-L; nao e a
gramatica textual final do TCF.H.

## Como rodar

Da raiz do repositorio:

```powershell
python experiments/lab/dirty/2026-07-13-1921-dataseth-typed-header-domain/run.py
```

O runner testa RT semantico, adaptacao de volta para primitivas Python,
distinctness e uma entrada malformada. Ele tambem prova que o payload de
strings de `HK` e byte-identico a um `tcf.encode(list[str])` comum.

## Evidencia gerada

- `artifacts/01-naive-counterexample.txt` - colisao obrigatoria da versao
  stringificada.
- `artifacts/02-hdom-sample.txt` - header de dominio tipado e indices packed.
- `artifacts/03-hk-sample.txt` - header de kinds e corpo composto.
- `artifacts/04-bytes-comparison.txt` - bytes somente depois de RT verde.
- `artifacts/05-hk-string-payload.tcf.txt` - payload TCF real usado por HK.
- `artifacts/06-hk-string-payload-obat-hcc-trace.txt` - SideOutputs desse
  payload.
- `artifacts/07-roundtrip.txt` - RT por perfil e por adaptador de saida.
- `artifacts/08-input-profiles.txt` - entradas sinteticas construidas para
  falsificar colisoes.

Leia [result.md](result.md) para a interpretacao e
[datasets-provenance.md](datasets-provenance.md) para limites da evidencia.

## Limites e proxima pergunta

O lab e uma coluna regular isolada. Ele ainda nao resolve definition/repetition
levels, arrays ragged, campos ausentes, contagem herdada de outro ramo, nem a
gramatica final do header. `n` aparece no prototipo porque um stream packed
precisa saber quantos indices decodificar; numa forma regular ele pode talvez
ser derivado do row group, mas isso precisa de prova separada.

Nao ha decisao de weld: `HDOM` so se aplica com dominio pequeno; `HK` adiciona
um stream de kinds e exige framing/contagem. A comparacao com a folha tipada
per-instance e com a forma regular `#TCF.8H` fica para P4/P5 do plano.