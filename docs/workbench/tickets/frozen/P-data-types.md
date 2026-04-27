---
title: Suporte a tipos de dados — binario, base64, datas, nulls, mixed types
type: research
status: OPEN
priority: MEDIUM
created: 2026-04-09
---

# Tipos de Dados no TCF

## Situacao atual

TCF trata tudo como texto (string). O encoder le CSV (tudo string),
resolve FKs, aplica RLE, e grava. Nao ha declaracao de tipo.

Nossos dados sinteticos tem:
- Strings (nomes: "Ana", "Caneta")
- Numeros (float: "2.50", int: "3")
- Datas (ISO: "2024-01-15")
- Booleanos (texto: "True"/"False")
- Nulls (string vazia "")

## O que NAO testamos

1. **Binario em base64** — se um campo CSV contem `aGVsbG8gd29ybGQ=`,
   o RLE nao comprime (cada valor e unico). Base64 e incompressivel por RLE.

2. **JSON nested** — se um campo contem `{"addr": {"city": "SP"}}`,
   o TCF trata como string opaca. Funciona mas perde estrutura.

3. **Blobs / imagens** — dados grandes por campo. CSV nao suporta
   nativamente, mas JSONL sim (base64 inline).

4. **Tipos declarados** — SQL tem `INT`, `VARCHAR`, `DATE`. JSON tem
   `number`, `string`, `boolean`, `null`. TCF nao declara tipo.

## Perguntas

### Para o encoder:
- Deveriamos declarar tipos no header? Ex: `## vendas n=509 types=str,str,date,int,float,float`
- Isso ajudaria LLMs? Ou e overhead sem beneficio?

### Para LLM comprehension:
- LLMs tratam tudo como token — tipo declarado importa?
- Base64 em campo: o RLE nao comprime, mas o modelo entenderia?
- Datas: "2024-01-15" vs "15/01/2024" vs epoch — qual formato melhor?

### Para compressao:
- Campos base64 sao incompressiveis por RLE (alta cardinalidade)
- Campos numericos com muitas casas decimais comprimem mal
- Campos boolean comprimem otimamente por RLE (2 valores unicos)

## Comparacao com outros formatos

| Formato | Tipos declarados | Binario | Nulls |
|---------|-----------------|---------|-------|
| CSV | Nao | Nao (exceto base64 inline) | String vazia |
| JSON/JSONL | Sim (number, string, bool, null) | Base64 inline | `null` |
| Parquet | Sim (schema completo) | Sim (nativo) | Bit mask |
| SQL | Sim (DDL) | BLOB | NULL |
| **TCF** | **Nao (tudo texto)** | **Nao testado** | **String vazia** |

## Possivel extensao (futuro)

```
# TCF v0.3 level=2
# types: pessoa=str, produto=str, dt=date, qtd=int, preco_unit=float, total=float
## vendas n=509 sorted_by=pessoa
```

Beneficio: LLM sabe que `total` e numerico sem precisar inferir.
Custo: mais linhas de header, mais complexidade no encoder/decoder.

## Decisao

Para o paper v1: documentar como **limitacao conhecida**.
TCF e texto-puro por design (simplicidade, LLM-friendly).
Tipos declarados podem ser extensao futura.

Testar com dados base64/mixed seria interessante mas ortogonal
ao escopo do paper (formato columnar vs row para raciocinio).

## Tarefas

- [ ] Pesquisar se Sui et al. 2024 ou outros testaram tipos de dados
- [ ] Verificar como LLMs lidam com base64 inline em CSV vs JSON
- [ ] Decidir se vale adicionar type hints opcionais no header
- [ ] Documentar como limitacao no paper
