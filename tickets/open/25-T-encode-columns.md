---
title: encode_columns() — core puro que aceita dict[str, list]
type: task
status: OPEN
priority: 24
parent: 24-M-phase2-tcf-refactor
---

# encode_columns()

## Objetivo

Criar a funcao core do encoder que aceita dados JA CARREGADOS,
sem fazer nenhum IO. E a "traducao pura" de dados para texto TCF.

## API proposta

```python
def encode_columns(
    table_name: str,
    columns: dict[str, list[str]],
    *,
    config: EncodeConfig | None = None,
) -> str:
    """Encode column-oriented data to TCF text.

    Args:
        table_name: name for the ## header (e.g. "lineitem")
        columns: {col_name: [val1, val2, ...]} — all lists same length
        config: compression level, stats, precision

    Returns:
        TCF formatted text string

    Raises:
        ValueError: if columns have different lengths
    """
```

## O que faz (passos 4-8 do encoder atual)

1. Validar que todas as colunas tem mesmo comprimento
2. Formatar numericos (`fmt_num`)
3. Sort colunar se level >= 2 (`sort_columns`)
4. Dict encoding se level >= 3 (`dict_build`)
5. RLE se level >= 1 (`rle_encode`)
6. Gerar STATS lines se solicitado
7. Montar texto TCF completo

## O que NAO faz (passos 1-3)

- NAO le arquivos do disco
- NAO le metadata.json
- NAO faz JOIN de tabelas
- NAO resolve FKs
- NAO importa csv, Path, json

Tudo isso vive nos wrappers (encode_from_csv, encode_rows).

## Implementacao

Extrair a logica dos passos 4-8 do `encode()` atual para uma funcao
nova. O `encode()` atual passa a chamar `encode_columns()` internamente.

## Relacao com encode_rows()

`encode_rows(list[dict])` converte para `dict[str, list]` e chama
`encode_columns()`. Ambas vivem em `src/tcf/encoder.py`.

## Tarefas

- [ ] Criar `encode_columns()` em `src/tcf/encoder.py`
- [ ] Extrair logica de passos 4-8 do `encode()` atual
- [ ] `encode()` antigo passa a ser wrapper
- [ ] Validacao de input (colunas com tamanhos diferentes)
- [ ] Testes unitarios diretos (sem CSV, sem filesystem)
- [ ] Todos os 112 testes existentes continuam passando
