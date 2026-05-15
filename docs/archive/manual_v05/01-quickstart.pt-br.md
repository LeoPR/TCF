# 01 — Quickstart (PT-BR)

## Instalação

```bash
pip install -e .
```

Requer Python 3.10+. Sem dependências externas para encode/decode core.

## Codificar uma tabela

```python
from tcf import encode_rows, EncodeConfig

linhas = [
    {"id": 1, "nome": "Alice", "idade": 30},
    {"id": 2, "nome": "Bob",   "idade": 30},
    {"id": 3, "nome": "Carol", "idade": 31},
]

texto = encode_rows("pessoas", linhas, config=EncodeConfig(level=2, include_stats=True))
print(texto)
```

Saída (L2 compacta com STATS):

```
# TCF v0.2 level=2
# N*val = val repeated N times

## pessoas n=3
# STATS id: n=3 sum=6 min=1 max=3 avg=2.00
# STATS idade: n=3 sum=91 min=30 max=31 avg=30.33
id:
1
2
3
nome:
Alice
Bob
Carol
idade:
2*30
31
```

## Codificar múltiplas tabelas

```python
cfg = EncodeConfig(level=2, include_stats=True)
partes = []
for tabela, linhas in {"pessoas": pessoas, "pedidos": pedidos}.items():
    partes.append(encode_rows(tabela, linhas, config=cfg))
payload = "\n\n".join(partes)
```

## Usar com LLM (padrão one-shot)

```python
import openai
client = openai.OpenAI()

prompt = f"""Voce e um analista de dados. Os dados abaixo estao em formato TCF:
- Cada coluna lista seus valores em sequencia
- "N*val" significa val repetido N vezes consecutivas (RLE)
- STATS no topo de cada tabela tem agregacoes pre-computadas

{payload}

## Pergunta
Quantas pessoas tem 30 anos?

## Resposta
"""

resp = client.responses.parse(
    model="gpt-5.4-nano",
    input=prompt,
    text_format=...  # ver capitulo 04
)
```

## Decodificar de volta para linhas

```python
from tcf import decode

restaurado = decode(texto)
# restaurado[0] == {"id": 1, "nome": "Alice", "idade": 30}
```

## Próximos passos

- [02 EN](02-encode-decode.md) — referência completa da API
- [03 EN](03-compression-levels.md) — escolher nível L0..L3
- [04 EN](04-llm-integration.md) — pipelines NL2SQL
- [05 PT-BR](05-recommended-models.pt-br.md) — modelos recomendados
