# Reference: knobs de `encode()`

Referência dos parâmetros opt-in de [`tcf.encode`](../../src/tcf/encoder.py). O uso sem argumentos
produz o formato **0.8** sem perdas (`#TCF.8M`, ou `#TCF.8R` se a entrada for lista de registros);
os parâmetros abaixo só mudam bytes/layout **quando passados explicitamente**.

<!-- doctest: skip -->
```python
from tcf import encode
encode(data, *, schema=None, side_outputs=None, parallel=False,
       layers=None, fallback=True, min_header=True, min_len=None, sort_by=None,
       name=None, stamp=None, drop_names=False)
```

Aplicam-se a **multi-coluna** (`dict[str, list[str]]`). Uma `list[dict]` retangular e plana é
a mesma tabela escrita de outro jeito, e desde o
[ADR-0049](../adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md) ela sai em **`#TCF.8R`**,
o wire multi com o discriminador trocado: os knobs de coluna valem lá igual, com duas
exceções que **levantam**, `sort_by` e `name`.

Para single-col (`list[str]`) valem `schema`, `min_len`, `stamp` e `name` (este só junto de
`schema`, porque ele rotula o header `#TCF.8 nome:spec`). **Todos os outros levantam**, e
desde 2026-09-01 nenhum é ignorado calado: `fallback`, `min_header`, `drop_names` e
`parallel` escolhem candidato por coluna, escrevem o meta por coluna, omitem nomes de coluna
ou paralelizam entre colunas, e uma lista de uma coluna não tem nada disso; o `sort_by` não
tem coluna nomeada para ordenar; o `name` sem `schema` não tem header para rotular.

O `min_len` é o único do grupo que **funciona** no single-col, e por isso é o único que
continua aceito: numa coluna de IDs zero-padded ele leva 46 B a 23 B, e em valores únicos
longos 363 B a 56 B. A matriz completa de quem vale em que entrada está em [api.md](api.md).
Output é sempre UTF-8, LF only. `decode(encode(x)) == x`, com o `sort_by` como única
ressalva (ver abaixo).

> **Previstos, ainda não implementados** (`.9`): `bn_modo` (`"B"` stream, default de hoje,
> vs `"C"` lote, `T-BN-LOTE`) e os **perfis macro** (`stream`/`lote`/`rapido`/`memoria`/
> `compacto`/`auto`, `T-PERFIS-MACRO`). A ideia dos perfis é declarar a **intenção** em vez do
> mecanismo, porque um knob por mecanismo não escala. `PipelineConfig` já é o precedente de
> agrupador. Esboço:
> `2026-08-07-flags-modo-bn-e-perfis-macro`.

## Knobs de bytes / layout

| knob | tipo | default | efeito | byte-impact |
|---|---|---|---|---|
| `fallback` | bool | `True` | por coluna escolhe `min(tcf, raw, dict, split)` | **zero-regressão** por construção (escolhe o menor) |
| `min_header` | bool | `True` | header mínimo (meta inline, tamanhos hex, última coluna sem size) | economiza bytes de header |
| `min_len` | int\|None | `None` (auto) | override do `min_len` do OBAT (afixos com `length < min_len` viram literal) | muda bytes só quando passado |
| `sort_by` | str\|None | `None` | **autoriza** reordenar as linhas pela coluna nomeada; o encoder emite as duas versões e fica com a menor | **zero-regressão** por construção (escolhe o menor), **order-free** |
| `drop_names` | bool | `False` | tira os nomes das colunas do header; a **ordem** passa a ser o contrato | economiza o header dos nomes (medido: 39 → 31 B em 2 colunas); o `decode` devolve `'0'`, `'1'`, ... |
| `stamp` | bool\|None | `None` | emite ou não a magic `#TCF.8` | só tem efeito em **single-col**: `False` tira a magic. Em multi-col a magic é estrutural e o knob não muda o wire |
| `name` | str\|None | `None` | rótulo do header em single-col **com** `schema` (`#TCF.8 nome:spec`) | soma o tamanho do rótulo; sem `schema` a chamada **levanta**, em vez de ignorar calado |

### `fallback` (default `True`)
Cada coluna é encodada por todos os modos disponíveis e fica com o menor: **tcf** (OBAT+HCC),
**raw** (`!`, V2-A), **dict** (`@`, V2-B), **split** (`%`, estrutural). Como escolhe estritamente o
menor, ligar nunca aumenta bytes. É o que põe colunas low-card em `@dict` automaticamente (e habilita
as queries lazy via dict-stream).
- `fallback=False` → mantém tcf em toda coluna (sem raw/dict/split).
- O formato continua `#TCF.8M`; o legado `.6/.7` é recuperado via git, não por este knob.

### `min_header` (default `True`)
Header compacto: meta inline após `#TCF.8M`, tamanhos em hexadecimal e **última coluna sem `size`** (corpo até EOF).
- `min_header=False` → todas as colunas não-anônimas recebem tamanho no meta.

### `min_len` (int ≥ 1, ou `None`)
`None` (default) = auto por coluna (`detect_min_len`, ADR-0010): comportamento inalterado.
Um `int` aplica o **mesmo** `min_len` a **todas** as colunas (tuning manual; muda os bytes).
`min_len < 1` levanta `ValueError`.

### `sort_by` (str, ou `None`): O-FMT-02
**Autoriza** reordenar as linhas pela coluna-chave antes de encodar, agrupando os valores
iguais dela. Desde o [ADR-0050](../adr/0050-sort-by-vira-candidato-o-floor-decide.md) a
ordenação é um **candidato**, não uma ordem: o encoder encoda as duas versões e emite a
menor, do mesmo jeito que o `fallback` já escolhe entre modos por coluna.
- **Nunca-pior, e é por isso que ele não garante ordenar.** Um wire pedido com `sort_by` pode
  voltar na ordem de entrada, se ordenar não tiver ajudado. Quem precisa da tabela ordenada
  de fato ordena as linhas na origem, antes de encodar.
- **Faixa medida**: **−43,0%** quando as colunas companheiras são função da chave, e
  **+52,1%** quando são independentes dela (60 linhas, ADR-0050). O saldo vira negativo já na
  segunda companheira independente, porque a permutação agrupa os iguais da chave e desarruma
  todas as outras colunas de uma vez. É essa cauda que o candidato apara.
- **Order-free**: quando o encoder ordena, o `decode` devolve a ordem **ordenada**, e a
  original **não** é recuperável. Use só quando a ordem não importa, **nunca** numa
  transmissão que precise preservá-la.
- **A chave de ordenação é `str(valor)`**, lexicográfica: `'10'` vem antes de `'2'`, e um
  `None` compara como a string `'None'`. É deliberado, e não um bug em aberto: a ordenação
  aqui existe para agrupar iguais, e qualquer ordem total agrupa igualmente bem.
- **`ValueError`** se a coluna não existe, em `list[str]` (não há coluna nomeada para ordenar)
  e em `list[dict]` (ali a ordem da lista é a unidade que o chamador vê, e reordená-la calado
  seria o silêncio que o formato recusa).

```python
from tcf import encode, decode

ganha = {"k":      ["2", "10", "2", "10", "3", "2", "10", "3"],
         "nome":   ["beta", "alfa", "beta", "alfa", "gama", "beta", "alfa", "gama"],
         "cidade": ["Recife", "Natal", "Recife", "Natal", "Belem", "Recife", "Natal", "Belem"]}

len(encode(ganha)), len(encode(ganha, sort_by="k"))    # 104, 98: ordenar encolhe
decode(encode(ganha, sort_by="k"))["k"]                # ['10','10','10','2','2','2','3','3']

perde = dict(ganha, nome=["a", "b", "c", "d", "e", "f", "g", "h"],
                    cidade=["p", "q", "r", "s", "t", "u", "v", "w"])

len(encode(perde)), len(encode(perde, sort_by="k"))    # 77, 77: o encoder desistiu
decode(encode(perde, sort_by="k"))["k"]                # ['2','10','2','10','3','2','10','3']
```

As duas chamadas pedem a mesma coisa sobre a mesma chave. Na primeira as companheiras são
função de `k`, e ordenar paga; na segunda são todas distintas, ordenar só desarrumaria, e o
wire volta idêntico ao que sairia sem o kwarg.

O layout contíguo que a [`view()`](lazy-view.md) usa deixou de ser garantia deste knob. O
`agg_by` cai sozinho no caminho order-free e nunca levanta por causa disso; o `group_ranges`
continua estrito, porque ele é o inspetor de layout.

## Knobs relacionados (não-byte)

| knob | efeito |
|---|---|
| `schema` | specs por coluna: `"cpf"` (name do registry), objeto spec, ou dict nome/posicao→spec; filtro opcional para CPF/CNPJ/IP; o encoder compara o blob completo e mantém a menor representação. Filtros oficiais decodificam sem argumento; customizados exigem o mesmo nome no cabeçalho. Ver [how-to/use-natures](../how-to/use-natures.md). |
| `parallel` | `True`/`int` paraleliza o encode das colunas (multi-col); **output byte-idêntico** ao serial. |
| `side_outputs` | captura logs/stats internos (`column_features`, `hcc_trace`, `seq_rle_runs`, `multi_info`, ...) sem custo quando ausente. |
| `layers` | `PipelineConfig` alternativo (avançado). |

## Notas de versão

O uso sem argumentos produz **0.8** (ADR-0032: projeto é pré-1.0; `#TCF.N` são marcadores de dev, não
contratos rígidos). Os invariantes byte-canonical (D1-D9 = 1545 B, D17a = 300 B) são pinados em
[`tests/test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py) e
re-pináveis só com ADR (ADR-0024/0025).

## Ver também

- [ADR-0022](../adr/0022-v2a-fallback-identity-weld.md) (V2-A `!`), [ADR-0025](../adr/0025-v2b-dictionary-categorical-weld.md) (V2-B `@`), [ADR-0026](../adr/0026-structural-split-weld.md) (split `%`)
- [ADR-0023](../adr/0023-v2-minimal-header-weld.md) (header mínimo)
- [ADR-0049](../adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md) (`#TCF.8R`, a forma da entrada como metadado), [ADR-0050](../adr/0050-sort-by-vira-candidato-o-floor-decide.md) (`sort_by` vira candidato)
- [docs/algorithms/TCF-format.md](../algorithms/TCF-format.md) (spec do formato)
- [how-to/inspect-compression.md](../how-to/inspect-compression.md)
