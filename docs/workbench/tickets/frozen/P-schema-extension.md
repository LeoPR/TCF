---
title: Extensao de schema — PK, FK, nullability, tipos, constraints
type: research
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Visao de TCF como formato de dados relacionais completo (alem de tabela flat)
see_also: P-data-types (tipos basicos), E-http-protocol (uso em APIs)
---

# Extensao de Schema: Modelagem Relacional Completa

## Visao

TCF atual trata dados como **uma tabela flat** (supertable). Perde a
riqueza de modelagem relacional: quais colunas sao chaves, quais sao
obrigatorias, quais relacionamentos existem.

Para ser **referencia de protocolo** (E-http-protocol), TCF precisa poder
expressar:
- **Primary Key (PK):** qual coluna identifica unicamente cada linha
- **Foreign Key (FK):** qual coluna referencia outra tabela/coluna
- **NOT NULL:** colunas obrigatorias
- **UNIQUE:** valores unicos (mesmo sem ser PK)
- **Tipos:** int, float, date, datetime, string, boolean (de P-data-types)
- **Check constraints:** "total >= 0", "qtd > 0" (opcional)
- **Relationships:** 1:N, N:M

## Proposta: header de schema expandido

```
# TCF v0.3 level=2
# schema {
#   tables: [
#     {name: clientes, pk: id, cols: [
#       {name: id, type: int, not_null: true, unique: true},
#       {name: nome, type: str, not_null: true}
#     ]},
#     {name: produtos, pk: id, cols: [...]},
#     {name: vendas, pk: id, cols: [
#       {name: id, type: int, not_null: true},
#       {name: id_cliente, type: int, not_null: true, fk: clientes.id},
#       {name: id_produto, type: int, not_null: true, fk: produtos.id},
#       {name: dt, type: date, not_null: true},
#       {name: qtd, type: int, not_null: true, check: "qtd > 0"},
#       {name: preco_unit, type: float},
#       {name: total, type: float, not_null: true}
#     ]}
#   ]
# }

## vendas n=509 sorted_by=id_cliente
...
```

Alternativa mais compacta (YAML-like):
```
# schema:
#   clientes: pk=id; id:int!uq; nome:str!
#   produtos: pk=id; id:int!uq; nome:str!
#   vendas:   pk=id; id:int!; id_cliente:int!->clientes.id; id_produto:int!->produtos.id; dt:date!; qtd:int!; preco_unit:float; total:float!
```

Legenda:
- `!` = NOT NULL
- `uq` = UNIQUE
- `->` = FK
- `pk=col` = primary key

## Perguntas de pesquisa

### RQ-S1: LLMs interpretam schema declarado?
Hipotese: dar `# schema` no header ajuda LLM a entender os dados
(similar a Sui 2024 self-augmentation +3.26%).

### RQ-S2: Schema declarado aumenta tamanho significativamente?
Header extra adiciona 200-2000 chars. Para tabelas pequenas e overhead
pesado. Para tabelas grandes e trivial.

### RQ-S3: Flat vs multi-table — qual performa melhor?
Atualmente fazemos JOIN flat (uma tabela). Com schema declarado,
podemos voltar a expor tabelas separadas (mais compacto?):

```
## clientes n=20
id: 1 2 3 ... 20
nome:
Ana
Bruno
...

## produtos n=20
...

## vendas n=509 sorted_by=id_cliente
id_cliente:
8*1
12*2
...
```

Compressao provavelmente melhor (IDs curtos em vez de nomes).
LLM entendimento — precisa testar.

## Relacao com alternativas

| Formato | Schema | TCF proposto |
|---------|--------|-------------|
| JSON Schema | Separado do dado | Inline no header |
| Protobuf | Separado (.proto) | Inline opcional |
| SQL DDL | Separado (CREATE TABLE) | Inline no header |
| Parquet | Binario embutido | Textual embutido |

**Vantagem TCF:** tudo em um arquivo texto, legivel por humanos e LLMs.

## Hipoteses testaveis

### H-schema-1: Schema ajuda LLM em FK resolution
Com `# schema vendas.id_cliente -> clientes.id`, LLM entende que
"id_cliente=3" significa "pessoa 3 da tabela clientes". Sem schema,
precisa inferir.

### H-schema-2: Schema multi-tabela comprime mais que flat
Tabelas separadas com IDs curtos comprimem melhor que supertable com
nomes longos repetidos.

### H-schema-3: Schema aumenta accuracy em questoes relacionais
Ex: "quantos clientes compraram produto X?" requer entender o relacionamento.

## Trade-offs

**Pro adicionar schema:**
- Formato mais rico e auto-descritivo
- LLMs entendem relacionamentos
- Compressao pode melhorar (tabelas separadas)
- Reversibilidade total garantida

**Contra:**
- Encoder mais complexo
- Parser mais complexo (implementacoes cross-language mais dificeis)
- Header mais pesado (overhead para tabelas pequenas)
- Quebra compatibilidade com v0.2 (versionar para v0.3)

## Tarefas

- [ ] Decidir sintaxe: YAML-like compact vs JSON full
- [ ] Prototipo em Python (v0.3 experimental)
- [ ] Testar compressao: flat vs multi-table + schema
- [ ] Testar LLM: accuracy com/sem schema header
- [ ] Testar LLM: flat vs multi-table
- [ ] Se beneficio > custo: promover para spec oficial
- [ ] Se nao: documentar como "nao foi adotado por X"
