# Cuidado com homonimos em key elimination (Proposta I)

**Data**: 2026-05-09
**Origem**: observacao do user durante EXP-004c
**Status**: registro durable; investigar quando key elimination for implementada

## Problema

Dados com **multiplos rows que tem o mesmo valor "natural"** mas IDs
diferentes podem ser colapsados se TCF eliminar a PK e usar o nome
como referencia.

### Exemplo

```
Original (com PK):
  id=1, nome=Ana, idade=25
  id=5, nome=Ana, idade=42      <- outra Ana, outra pessoa!
  id=12, nome=Ana, idade=30     <- ainda outra
```

Se TCF aplicar key elimination (Proposta I) e tratar `nome` como
identificador unico:

```
Risco — colapso indevido:
  # dict nome: Ana
  nome: 1, 1, 1
  idade: 25, 42, 30
```

Decoder regenera: `id=1, nome=Ana, idade=25 / id=2, nome=Ana, idade=42 / id=3, nome=Ana, idade=30`.

A **relacao foi preservada** (3 Anas com idades distintas), mas **se
o sistema externo dependia de id=1 vs id=5 vs id=12** para distinguir,
a informacao se perdeu.

## Por que isso importa

A Proposta I (key elimination) ja foi registrada com a ressalva de que
preserva **relacao**, nao **valores literais** das chaves. Mas os
4 graus (0/1/2/3) precisam ser refinados:

| Grau | Tipo | Risco com homonimos |
|------|------|---------------------|
| 0 | UUID universal | sem risco — UUID eh unico por construcao |
| 1 | Natural com semantica externa (CPF, EAN) | sem risco — externa eh unica |
| 2 | Sintetica local (auto-increment) | **RISCO**: pode colapsar homonimos se eliminar |
| 3 | Derivada/composta interna | depende — se inclui campo discriminador, ok |

**Caso especifico de risco**: PK grau 2 onde a tabela tem **valores
duplicados em colunas naturais** (ex: 2 pessoas com mesmo nome).

## Distincao importante

Este problema **nao afeta**:

1. **DICT implicito (flag D)** — refs sao por linha, nao por valor.
   Cada linha tem sua propria entrada no dict. `nome: 1, 1, 1` sao
   3 linhas separadas que apontam para mesma entrada do dict — ok,
   reconstroe 3 Anas.

2. **Sort + RLE (flags S+R)** — agrupa contiguos mas nao colapsa.

3. **Cross-DICT (Proposta E)** — mesma logica, refs por linha.

O problema **so existe** quando se decide **descartar a PK
explicita** e usar uma coluna natural como identificador unico.

## Solucao a investigar (quando implementar Proposta I)

Antes de eliminar PK grau 2, verificar:

```python
def can_eliminate_pk(rows, pk_col, natural_cols):
    """Retorna True se eliminar PK preserva distincao linha-a-linha."""
    # 1. Se TCF preserva ordem original e numero de linhas: sempre ok
    #    (decoder regenera ids 1..N e cada linha mantem seus dados)
    # 2. Se TCF deduplicar linhas inteiras: NAO ok se houver duplicatas
    #    em natural_cols mas distincao na PK eliminada
    duplicates_in_natural = (
        len(rows) > len({tuple(r[c] for c in natural_cols) for r in rows})
    )
    if duplicates_in_natural:
        # PK estava distinguindo dois rows com mesmas naturais
        return False
    return True
```

**Insight chave**: enquanto TCF v0.5 emite **uma linha por row** (nao
deduplica), eliminar PK eh seguro — decoder regenera ids 1..N e cada
linha preserva seu conteudo. Homonimos viram rows distintos com
nomes iguais, exatamente como na fonte.

**O risco aparece se** algum modo agressivo de TCF (futuro) decidir
**deduplicate rows inteiras** combinado com key elimination.

## Acao registrada

1. Manter este documento como referencia ao implementar Proposta I
2. Criar ticket para revisar quando chegar a hora
3. Em testes formais (futuros), incluir cenarios com homonimos
   propositais para validar comportamento

## Cenarios de teste sugeridos para implementacao futura

```
T1: 1000 pessoas, 50 nomes distintos, ids unicos
   - Encode com key elimination
   - Decode
   - Verificar: 1000 rows preservadas (homonimos mantidos)

T2: 1000 pessoas com 100 nomes, todas distinguidas por (nome, idade)
   - PK eliminavel apenas se TCF NAO deduplicar (nome, idade)
   
T3: pior caso — 100 pessoas, 5 nomes, 3 idades, multiplas combinacoes
   exatas duplicadas
   - Cuidado: aqui ate o ID natural (nome+idade) nao distingue
   - PK deve permanecer
```

## Relacionado

- [H-compression-v04-roadmap](../tickets/open/H-compression-v04-roadmap.md) — Proposta I
- [B-homonyms-key-collision (a criar)](../tickets/open/B-homonyms-key-collision.md)
